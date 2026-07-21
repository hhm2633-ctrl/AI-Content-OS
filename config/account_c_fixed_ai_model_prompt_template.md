# Account C Fixed AI Model Prompt Contract

Model ID: `account_c_fixed_model_01`

Use case: `identity-preserve`

Until the owner approves a full view set, every auxiliary human-scene edit for Account C must start
from the original reference itself. Do not regenerate the person from a prompt and do not use an
unapproved generated view as the next identity source.

1. `authoritative_sources/source_reference.png` — sole authoritative identity
2. `openai_edit_v2/<nearest-view>.png` — usable only after explicit owner approval

Prompt invariant block:

> Show exactly `account_c_fixed_model_01`. Preserve the registered face geometry, age impression,
> skin tone, hairline, body build, shoulder width, arm and leg thickness, waist/hip balance, and
> torso/leg proportions. Change only the requested expression, pose, wardrobe, background,
> lighting, and camera composition. Do not beautify, slim, enlarge the eyes, alter the nose or jaw,
> change age, change ethnicity, or change body type. If the requested scene conflicts with identity
> preservation, preserve identity and simplify the scene.

Use OpenAI direct image editing with high input fidelity and change only one requested element per
edit. Reject the result when any face or body invariant differs visibly from the original. Do not
repair a rejected identity by treating the drifted output as a new reference. Label accepted public
uses as `AI 연출 이미지`.

Allowed role: auxiliary lifestyle or explanatory scene for Account C fashion/beauty/commerce.

Forbidden roles: celebrity, witness, real customer, unverified brand model, product evidence, news
evidence, source footage, or testimonial.
