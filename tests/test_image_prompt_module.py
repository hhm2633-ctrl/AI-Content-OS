"""Independent coverage for modules/image_prompt/image_prompt_module.py.

Priority-2 gap-fill test: this module has no dedicated test file today
despite already supporting clean dependency injection (`llm_client=`
constructor kwarg), making it one of the easiest "zero test" modules to
cover safely. Uses a fake LLM client only -- no real OpenAI call, no
existing module or test file is modified.
"""

import json
import unittest

from modules.image_prompt.image_prompt_module import ImagePromptModule


class _FakeLLMClient:
    def __init__(self, response_text=None, raise_error=None):
        self.response_text = response_text
        self.raise_error = raise_error
        self.calls = []

    def generate_text(self, system_prompt, user_prompt, **kwargs):
        self.calls.append({"system_prompt": system_prompt, "user_prompt": user_prompt})
        if self.raise_error:
            raise self.raise_error
        return self.response_text


def _valid_llm_response():
    return json.dumps({
        "title": "LLM Title",
        "image_prompts": [
            {"page": 1, "role": "hook", "prompt": "hook prompt", "style": "clean", "ratio": "1:1"},
            {"page": 2, "role": "problem", "prompt": "problem prompt", "style": "clean", "ratio": "1:1"},
            {"page": 3, "role": "solution", "prompt": "solution prompt", "style": "clean", "ratio": "1:1"},
            {"page": 4, "role": "cta", "prompt": "cta prompt", "style": "clean", "ratio": "1:1"},
        ],
        "status": "image_prompts_created",
    })


class ImagePromptModuleSkipPathTests(unittest.TestCase):
    def test_need_ai_image_false_skips_llm_entirely(self):
        fake_client = _FakeLLMClient(response_text=_valid_llm_response())
        module = ImagePromptModule(llm_client=fake_client)

        result = module.run(
            content_result={"title": "Test"},
            image_strategy_result={"need_ai_image": False, "content_type": "news", "image_source": "thumbnail"},
        )

        self.assertEqual(result["status"], "image_prompts_skipped")
        self.assertTrue(result["ai_image_skipped"])
        self.assertEqual(result["image_prompts"], [])
        self.assertEqual(fake_client.calls, [])  # LLM never invoked

    def test_skipped_result_preserves_image_strategy_metadata(self):
        module = ImagePromptModule(llm_client=_FakeLLMClient())
        result = module.run(
            content_result={"title": "Test"},
            image_strategy_result={
                "need_ai_image": False,
                "content_type": "community",
                "image_source": "screenshot",
                "reason": "real source available",
                "image_usage_plan": {"mode": "real_image_required"},
            },
        )

        self.assertEqual(result["image_strategy"]["content_type"], "community")
        self.assertEqual(result["image_strategy"]["image_source"], "screenshot")
        self.assertEqual(result["image_strategy"]["reason"], "real source available")
        self.assertEqual(result["image_strategy"]["image_usage_plan"], {"mode": "real_image_required"})


class ImagePromptModuleLLMPathTests(unittest.TestCase):
    def test_valid_llm_response_is_used_without_fallback(self):
        fake_client = _FakeLLMClient(response_text=_valid_llm_response())
        module = ImagePromptModule(llm_client=fake_client)

        result = module.run(content_result={"title": "Real Title", "slides": []})

        self.assertEqual(result["status"], "image_prompts_created")
        self.assertFalse(result["fallback_used"])
        self.assertEqual(len(result["image_prompts"]), 4)
        self.assertEqual(result["image_prompts"][0]["role"], "hook")
        self.assertEqual(len(fake_client.calls), 1)

    def test_llm_called_with_need_ai_image_true(self):
        fake_client = _FakeLLMClient(response_text=_valid_llm_response())
        module = ImagePromptModule(llm_client=fake_client)

        module.run(
            content_result={"title": "Real Title"},
            image_strategy_result={"need_ai_image": True},
        )

        self.assertEqual(len(fake_client.calls), 1)

    def test_missing_title_falls_back_to_llm_provided_title_when_present(self):
        fake_client = _FakeLLMClient(response_text=_valid_llm_response())
        module = ImagePromptModule(llm_client=fake_client)
        result = module.run(content_result={})
        self.assertEqual(result["title"], "LLM Title")

    def test_llm_response_missing_title_falls_back_to_content_title(self):
        response = json.loads(_valid_llm_response())
        del response["title"]
        fake_client = _FakeLLMClient(response_text=json.dumps(response))
        module = ImagePromptModule(llm_client=fake_client)

        result = module.run(content_result={"title": "Content Title"})
        self.assertEqual(result["title"], "Content Title")

    def test_llm_response_with_fewer_than_four_prompts_is_padded(self):
        response = {
            "title": "T",
            "image_prompts": [{"page": 1, "role": "hook", "prompt": "only one"}],
            "status": "image_prompts_created",
        }
        fake_client = _FakeLLMClient(response_text=json.dumps(response))
        module = ImagePromptModule(llm_client=fake_client)

        result = module.run(content_result={"title": "T"})
        self.assertEqual(len(result["image_prompts"]), 4)
        self.assertEqual(result["image_prompts"][0]["prompt"], "only one")
        # Slides 2-4 padded from the fallback generator, not left empty/missing.
        for entry in result["image_prompts"][1:]:
            self.assertTrue(entry["prompt"])

    def test_non_json_llm_response_triggers_full_fallback(self):
        fake_client = _FakeLLMClient(response_text="this is not json at all")
        module = ImagePromptModule(llm_client=fake_client)

        result = module.run(content_result={"title": "Fallback Title"})

        self.assertTrue(result["fallback_used"])
        self.assertIn("llm_or_json_parse_failed", result["fallback_reason"])
        self.assertEqual(len(result["image_prompts"]), 4)
        self.assertEqual(result["status"], "image_prompts_created")  # never a failed workflow status

    def test_llm_failed_status_in_response_triggers_fallback(self):
        response = json.dumps({"status": "llm_failed", "error": "quota exceeded"})
        fake_client = _FakeLLMClient(response_text=response)
        module = ImagePromptModule(llm_client=fake_client)

        result = module.run(content_result={"title": "T"})
        self.assertTrue(result["fallback_used"])
        self.assertIn("quota exceeded", result["fallback_reason"])

    def test_llm_response_missing_image_prompts_key_triggers_fallback(self):
        fake_client = _FakeLLMClient(response_text=json.dumps({"title": "T", "status": "image_prompts_created"}))
        module = ImagePromptModule(llm_client=fake_client)

        result = module.run(content_result={"title": "T"})
        self.assertTrue(result["fallback_used"])
        self.assertEqual(len(result["image_prompts"]), 4)

    def test_llm_response_that_is_a_json_list_not_dict_triggers_fallback(self):
        fake_client = _FakeLLMClient(response_text=json.dumps(["not", "a", "dict"]))
        module = ImagePromptModule(llm_client=fake_client)

        result = module.run(content_result={"title": "T"})
        self.assertTrue(result["fallback_used"])

    def test_llm_client_raising_exception_returns_structured_fallback(self):
        secret = "sk-secret-must-not-leak"
        fake_client = _FakeLLMClient(raise_error=RuntimeError(f"network down {secret}"))
        module = ImagePromptModule(llm_client=fake_client)

        result = module.run(content_result={"title": "T"})

        self.assertEqual(result["status"], "image_prompts_created")
        self.assertTrue(result["fallback_used"])
        self.assertEqual(result["fallback_reason"], "llm_generate_text_exception")
        self.assertEqual(len(result["image_prompts"]), 4)
        self.assertEqual(result["service_diagnostic"]["error_code"], "llm_call_error")
        self.assertNotIn(secret, json.dumps(result))
        self.assertEqual(len(fake_client.calls), 1)

    def test_llm_timeout_exception_uses_safe_timeout_code(self):
        fake_client = _FakeLLMClient(raise_error=TimeoutError("request details"))
        module = ImagePromptModule(llm_client=fake_client)

        first = module.run(content_result={"title": "T"})
        second = module.run(content_result={"title": "T"})

        self.assertEqual(first["service_diagnostic"]["error_code"], "llm_timeout")
        self.assertEqual(first["image_prompts"], second["image_prompts"])

    def test_fallback_prompts_use_slide_headlines_when_no_llm_response(self):
        fake_client = _FakeLLMClient(response_text="not json")
        module = ImagePromptModule(llm_client=fake_client)

        slides = [
            {"page": 1, "role": "hook", "headline": "Hook Headline"},
            {"page": 2, "role": "problem", "headline": "Problem Headline"},
            {"page": 3, "role": "solution", "headline": "Solution Headline"},
            {"page": 4, "role": "cta", "headline": "CTA Headline"},
        ]
        result = module.run(content_result={"title": "T", "slides": slides})

        self.assertIn("Hook Headline", result["image_prompts"][0]["prompt"])
        self.assertIn("Problem Headline", result["image_prompts"][1]["prompt"])

if __name__ == "__main__":
    unittest.main()
