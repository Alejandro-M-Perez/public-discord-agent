# Test Plan

## Required tests

### Trust routing
- owner ID -> trusted
- non-owner ID -> untrusted
- missing ID -> untrusted

### Channel policy
- owner in DM -> trusted allowed
- owner in admin channel -> trusted allowed
- owner in non-admin public channel -> expected downgraded or refused behavior
- non-owner in any channel -> untrusted

### Model routing
- trusted policy selects `openai/gpt-trusted`
- untrusted policy selects `lmstudio/local-public`
- untrusted cannot route to hosted model

### Tool firewall
- trusted can invoke approved tools
- trusted cannot invoke unapproved tools
- untrusted cannot invoke privileged tools

### Session isolation
- owner uses `owner:<OWNER_ID>`
- public user uses `public:<USER_ID>`
- public user cannot read or reuse owner namespace
- one public user cannot read another public user's namespace unless explicitly designed later

### Fail-closed behavior
- invalid route config defaults to untrusted
- missing channel config defaults to untrusted
- missing model config for public does not escalate to hosted
