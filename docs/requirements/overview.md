# Requirements Overview — telegram-digest-bot

## Goal

A web application that reads selected public Telegram channels and generates a short AI digest
for a requested time period, viewable in a browser by end users.

## Primary user

End users accessing a deployed public web application via browser.

## Success criteria

- Users can specify one or more public Telegram channels and a time range.
- The app fetches messages from the selected channels for that period.
- An AI model summarises the messages into a concise digest.
- The digest is displayed clearly in the browser.

## Out of scope

- No mobile app (web only).
- No real-time chat or two-way messaging with Telegram.
