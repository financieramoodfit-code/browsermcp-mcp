// Reconstructed from @r2r/messaging (monorepo package `packages-r2r/messaging`).
// The WebSocket RPC envelope used between the MCP server and the Browser MCP
// Chrome extension.

export const MESSAGE_RESPONSE_TYPE = "messageResponse";

/** A request sent from the server to the extension. */
export interface SocketMessageRequest<T = string, P = unknown> {
  id: string;
  type: T;
  payload: P;
}

/** The response envelope the extension sends back for a request. */
export interface SocketMessageResponse<R = unknown> {
  type: typeof MESSAGE_RESPONSE_TYPE;
  payload: {
    requestId: string;
    result?: R;
    error?: string;
  };
}
