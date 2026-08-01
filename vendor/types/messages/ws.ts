// Reconstructed from @repo/types (monorepo package `packages/types`).
// Describes the WebSocket messages exchanged with the Browser MCP extension:
// for each message name, the request `payload` and the `response` shape.

import { z } from "zod";

import {
  ClickTool,
  DragTool,
  HoverTool,
  NavigateTool,
  PressKeyTool,
  SelectOptionTool,
  TypeTool,
  WaitTool,
} from "../mcp/tool";

export interface ConsoleLog {
  type: string;
  text: string;
  timestamp?: number;
}

export type SocketMessageMap = {
  // Navigation
  browser_navigate: {
    payload: z.infer<typeof NavigateTool.shape.arguments>;
    response: void;
  };
  browser_go_back: { payload: Record<string, never>; response: void };
  browser_go_forward: { payload: Record<string, never>; response: void };

  // Interaction
  browser_click: {
    payload: z.infer<typeof ClickTool.shape.arguments>;
    response: void;
  };
  browser_drag: {
    payload: z.infer<typeof DragTool.shape.arguments>;
    response: void;
  };
  browser_hover: {
    payload: z.infer<typeof HoverTool.shape.arguments>;
    response: void;
  };
  browser_type: {
    payload: z.infer<typeof TypeTool.shape.arguments>;
    response: void;
  };
  browser_select_option: {
    payload: z.infer<typeof SelectOptionTool.shape.arguments>;
    response: void;
  };
  browser_press_key: {
    payload: z.infer<typeof PressKeyTool.shape.arguments>;
    response: void;
  };
  browser_wait: {
    payload: z.infer<typeof WaitTool.shape.arguments>;
    response: void;
  };

  // Snapshot / inspection
  browser_snapshot: { payload: Record<string, never>; response: string };
  browser_screenshot: { payload: Record<string, never>; response: string };
  browser_get_console_logs: {
    payload: Record<string, never>;
    response: ConsoleLog[];
  };

  // Page metadata
  getUrl: { payload: undefined; response: string };
  getTitle: { payload: undefined; response: string };
};
