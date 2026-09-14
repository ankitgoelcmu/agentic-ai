# middleware.py
import json

from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import ToolMessage


class LoopDetectionMiddleware(AgentMiddleware):
    """Generic loop detection for ANY tool, custom or built-in. Tracks
    (tool name, arguments) signatures already executed in this run, and
    short-circuits a repeat by returning a corrective ToolMessage instead
    of letting the real tool execute again. This replaces the need for
    separate hand-written counters in sigma_search, tavily_search, and
    sigma_validate, one general mechanism instead of three duplicated ones.
    """

    def __init__(self, max_repeats: int = 1):
        super().__init__()
        self.max_repeats = max_repeats
        self._call_counts = {}

    def _signature(self, tool_call):
        try:
            args_str = json.dumps(tool_call["args"], sort_keys=True, default=str)
        except TypeError:
            args_str = str(tool_call["args"])
        return (tool_call["name"], args_str)

    def reset(self) -> None:
        """Call before each new agent.invoke() to clear state between runs."""
        self._call_counts = {}

    def wrap_tool_call(self, request, handler):
        tool_call = request.tool_call
        signature = self._signature(tool_call)
        count = self._call_counts.get(signature, 0)

        if count >= self.max_repeats:
            return ToolMessage(
                content=(
                    f"You already called {tool_call['name']} with these exact "
                    f"arguments. Do not repeat it, proceed with the task using "
                    f"what you already have."
                ),
                tool_call_id=tool_call["id"],
                name=tool_call["name"],
            )

        self._call_counts[signature] = count + 1
        return handler(request)  # let the real tool run as normal