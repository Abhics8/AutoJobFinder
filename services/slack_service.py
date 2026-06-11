"""Slack DM wrapper. Falls back to console output if no token configured."""
import config

_client = None


def send_dm(text: str) -> bool:
    global _client
    if not config.SLACK_BOT_TOKEN or not config.SLACK_USER_ID:
        print("  [slack not configured — printing alert]\n" + text)
        return True
    if _client is None:
        from slack_sdk import WebClient
        _client = WebClient(token=config.SLACK_BOT_TOKEN)
    resp = _client.chat_postMessage(channel=config.SLACK_USER_ID, text=text,
                                    unfurl_links=False)
    return bool(resp.get("ok"))
