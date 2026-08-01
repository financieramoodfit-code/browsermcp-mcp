// Reconstructed from @r2r/messaging (monorepo package `packages-r2r/messaging`).
// Implements request/response messaging over a WebSocket: each request gets a
// unique id, and the matching response is resolved by `requestId`.

import { WebSocket } from "ws";

import { MESSAGE_RESPONSE_TYPE, SocketMessageResponse } from "./types";

type PayloadOf<MessageMap, T extends keyof MessageMap> = MessageMap[T] extends {
  payload: infer P;
}
  ? P
  : never;

type ResponseOf<MessageMap, T extends keyof MessageMap> = MessageMap[T] extends {
  response: infer R;
}
  ? R
  : unknown;

export function createSocketMessageSender<MessageMap>(ws: WebSocket) {
  async function sendSocketMessage<T extends keyof MessageMap & string>(
    type: T,
    payload: PayloadOf<MessageMap, T>,
    options: { timeoutMs?: number } = { timeoutMs: 30000 },
  ): Promise<ResponseOf<MessageMap, T>> {
    const { timeoutMs } = options;
    const id = generateId();
    const message = { id, type, payload };
    return new Promise((resolve, reject) => {
      const cleanup = () => {
        removeSocketMessageResponseListener();
        ws.removeEventListener("error", errorHandler);
        ws.removeEventListener("close", cleanup);
        clearTimeout(timeoutId);
      };
      let timeoutId: ReturnType<typeof setTimeout> | undefined;
      if (timeoutMs) {
        timeoutId = setTimeout(() => {
          cleanup();
          reject(new Error(`WebSocket response timeout after ${timeoutMs}ms`));
        }, timeoutMs);
      }
      const removeSocketMessageResponseListener =
        addSocketMessageResponseListener(ws, (responseMessage) => {
          const { payload } = responseMessage;
          if (payload.requestId !== id) {
            return;
          }
          const { result, error } = payload;
          if (error) {
            reject(new Error(error));
          } else {
            resolve(result as ResponseOf<MessageMap, T>);
          }
          cleanup();
        });
      const errorHandler = (_event: unknown) => {
        cleanup();
        reject(new Error("WebSocket error occurred"));
      };
      ws.addEventListener("error", errorHandler);
      ws.addEventListener("close", cleanup);
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify(message));
      } else {
        cleanup();
        reject(new Error("WebSocket is not open"));
      }
    });
  }
  return { sendSocketMessage };
}

function addSocketMessageResponseListener(
  ws: WebSocket,
  typeListener: (message: SocketMessageResponse) => void | Promise<void>,
) {
  const listener = async (event: { data: unknown }) => {
    const message = JSON.parse(
      (event.data as { toString(): string }).toString(),
    ) as SocketMessageResponse;
    if (message.type !== MESSAGE_RESPONSE_TYPE) {
      return;
    }
    await typeListener(message);
  };
  ws.addEventListener("message", listener as any);
  return () => ws.removeEventListener("message", listener as any);
}

function generateId(): string {
  if (typeof globalThis.crypto?.randomUUID === "function") {
    return globalThis.crypto.randomUUID();
  }
  const timestamp = Date.now().toString(36);
  const randomStr = Math.random().toString(36).substring(2, 10);
  return `${timestamp}-${randomStr}`;
}
