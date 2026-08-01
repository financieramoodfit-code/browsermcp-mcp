// Reconstructed from @repo/messaging (monorepo package `packages/messaging`).
// Generic type helpers for indexing into a socket message map.

/** The union of message names declared by a message map. */
export type MessageType<MessageMap> = keyof MessageMap & string;

/** The request payload type for a given message. */
export type MessagePayload<
  MessageMap,
  T extends keyof MessageMap,
> = MessageMap[T] extends { payload: infer P } ? P : never;

/** The response type for a given message. */
export type MessageResponse<
  MessageMap,
  T extends keyof MessageMap,
> = MessageMap[T] extends { response: infer R } ? R : unknown;
