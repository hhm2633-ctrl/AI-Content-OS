# CardNews rights intake fixture

This directory contains an offline, first-party **technical integration fixture**.
It is not a publish-approved image package.

`intake_manifest.json` is intentionally labelled
`technical_fixture_not_publish_approved`. The test creates the referenced PNG
from the checked-in pixel specification; no web asset, screenshot, external API,
or inferred licence is used. `ownership_record.txt` records only ownership of
that generated test bitmap.

For a real publishing review, an operator must replace the fixture values with:

1. the repository-relative path of the supplied, decodable image;
2. its real source URL and source name;
3. timezone-aware capture time;
4. copyright status and matching permission evidence tied to that exact path;
5. human topic-relevance review and timezone-aware review time; and
6. the attribution requirement and exact display text.

The validator result always retains `manual_image_required=true`,
`publishing_ready=false`, and `real_image_gate.satisfied=false`. A structurally
valid intake must still be rendered and manually reviewed in the normal workflow.

