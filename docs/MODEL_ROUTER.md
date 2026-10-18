# Model router
Default provider design: OpenAI/ChatGPT with OpenAI-compatible messages and response contracts. Current implementation is MockModel only and never opens a connection. 9Router can be added behind this contract later; not configured now.

ChatGPT subscription does not provide free OpenAI API billing. API key, separate API billing confirmation, monthly/per-task budget and permitted model/data policy are prerequisites. No live calls or charges, no automatic paid fallback. Future limits require provider-side controls where supported plus application accounting; estimates alone cannot guarantee a hard billing cap.
