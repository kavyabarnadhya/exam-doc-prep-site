# exam-doc-prep-site

Public site for the Exam Doc Prep Android app, served by GitHub Pages.

- `rules/v1/rules.json` + `rules/v1/rules.json.sig`: the Ed25519-signed exam-rules file the app downloads. Built and signed in the app repo with `dart run tool/rules_tool.dart build`; copy both files here unchanged. Never edit them by hand (the signature would fail and phones would reject the file).
- `privacy/index.html` and `terms/index.html`: the privacy policy and terms of use, styled by `site.css`. The wording is owner-approved; change it only with approval, and set the "Last updated" date when publishing.
