# Feature 001 — Hello World

## User story
As a developer setting up this project, I want the app to render a greeting that includes the project name, so I can confirm the build, dev server, and component pipeline work end to end.

## Acceptance criteria
- GIVEN the project name
  WHEN I open the dev server in a browser
  THEN I see an `<h1>` element containing "Welcome to telegram-digest-bot".
- GIVEN the pure `greeting(name)` function
  WHEN called with the project name
  THEN it returns a string containing that name.

## Out of scope
- Styling beyond minimal inline padding/font.
- Internationalization, theming, routing.

## Open questions
- None.
