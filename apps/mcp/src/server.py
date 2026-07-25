import logging
from dataclasses import dataclass
from typing import Annotated, Awaitable, Callable

from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations
from pydantic import AnyHttpUrl, BaseModel, Field

from adapters import HealthClient, HomelabApiClient
from auth import MCP_READ_SCOPE, StaticBearerTokenVerifier
from errors import McpServiceError
from metrics import observe_tool
from models import (
    ActiveRemindersResponse,
    AgendaTodayResponse,
    EventsUpcomingResponse,
    Reminder,
    ReminderListResponse,
    ServicesHealthResponse,
)

logger = logging.getLogger("mcp.operations")

Hours = Annotated[int, Field(ge=1, le=168)]
DueSoonDays = Annotated[int, Field(ge=1, le=90)]
ReminderId = Annotated[int, Field(ge=1)]
PageLimit = Annotated[int, Field(ge=1, le=500)]
PageOffset = Annotated[int, Field(ge=0)]

READ_ONLY_ANNOTATIONS = ToolAnnotations(
    readOnlyHint=True,
    openWorldHint=False,
)


@dataclass(frozen=True)
class ServerDependencies:
    api: HomelabApiClient
    health: HealthClient


def create_mcp_server(
    dependencies: ServerDependencies,
    *,
    allowed_hosts: list[str],
    allowed_origins: list[str],
    external_url: AnyHttpUrl,
    inbound_bearer_token: str = "",
    name: str = "Homelab MCP",
) -> FastMCP:
    token_verifier = (
        StaticBearerTokenVerifier(inbound_bearer_token)
        if inbound_bearer_token
        else None
    )
    auth_settings = (
        AuthSettings(
            issuer_url=external_url,
            resource_server_url=external_url,
            required_scopes=[MCP_READ_SCOPE],
        )
        if token_verifier
        else None
    )
    mcp = FastMCP(
        name,
        instructions=(
            "Read-only access to personal agenda, reminders, and allowlisted "
            "homelab service health. This server cannot mutate homelab state."
        ),
        stateless_http=True,
        json_response=True,
        auth=auth_settings,
        token_verifier=token_verifier,
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=allowed_hosts,
            allowed_origins=allowed_origins,
        ),
    )

    @mcp.tool(annotations=READ_ONLY_ANNOTATIONS)
    async def agenda_today(
        hours: Hours = 24,
        due_soon_days: DueSoonDays = 7,
    ) -> AgendaTodayResponse:
        """Get today's agenda, reminder groups, events, and data freshness."""
        return await _execute_tool(
            "agenda_today",
            lambda: dependencies.api.get_agenda(
                hours=hours,
                due_soon_days=due_soon_days,
            ),
        )

    @mcp.tool(annotations=READ_ONLY_ANNOTATIONS)
    async def events_upcoming(hours: Hours = 24) -> EventsUpcomingResponse:
        """Get upcoming events within a bounded time window."""
        return await _execute_tool(
            "events_upcoming",
            lambda: dependencies.api.get_upcoming_events(hours=hours),
        )

    @mcp.tool(annotations=READ_ONLY_ANNOTATIONS)
    async def reminders_list(
        include_completed: bool = False,
        limit: PageLimit = 100,
        offset: PageOffset = 0,
    ) -> ReminderListResponse:
        """List reminders with bounded pagination."""
        reminders = await _execute_tool(
            "reminders_list",
            lambda: dependencies.api.list_reminders(
                include_completed=include_completed,
                limit=limit,
                offset=offset,
            ),
        )
        return ReminderListResponse(
            reminders=reminders,
            include_completed=include_completed,
            limit=limit,
            offset=offset,
        )

    @mcp.tool(annotations=READ_ONLY_ANNOTATIONS)
    async def reminder_get(reminder_id: ReminderId) -> Reminder:
        """Get one reminder by its positive numeric ID."""
        return await _execute_tool(
            "reminder_get",
            lambda: dependencies.api.get_reminder(reminder_id),
        )

    @mcp.tool(annotations=READ_ONLY_ANNOTATIONS)
    async def services_health() -> ServicesHealthResponse:
        """Check the fixed deployment-configured service health allowlist."""
        return await _execute_tool(
            "services_health",
            dependencies.health.check_all,
        )

    @mcp.resource("homelab://agenda/today", mime_type="application/json")
    async def agenda_today_resource() -> str:
        """Get the default daily agenda as JSON context."""
        agenda = await _execute_resource(
            "homelab://agenda/today",
            lambda: dependencies.api.get_agenda(hours=24, due_soon_days=7),
        )
        return agenda.model_dump_json()

    @mcp.resource("homelab://reminders/active", mime_type="application/json")
    async def active_reminders_resource() -> str:
        """Get currently active reminders as JSON context."""
        agenda = await _execute_resource(
            "homelab://reminders/active",
            lambda: dependencies.api.get_agenda(hours=24, due_soon_days=7),
        )
        resource = ActiveRemindersResponse(
            generated_at=agenda.generated_at,
            reminders=agenda.reminders.active,
        )
        return resource.model_dump_json()

    @mcp.resource("homelab://services/health", mime_type="application/json")
    async def services_health_resource() -> str:
        """Get allowlisted service health as JSON context."""
        health = await _execute_resource(
            "homelab://services/health",
            dependencies.health.check_all,
        )
        return health.model_dump_json()

    return mcp


async def _execute_tool[ResultT](
    name: str,
    operation: Callable[[], Awaitable[ResultT]],
) -> ResultT:
    with observe_tool(name):
        try:
            result = await operation()
        except McpServiceError as exc:
            logger.warning(
                "tool failed",
                extra={"tool": name, "error_type": type(exc).__name__},
            )
            raise ToolError(str(exc)) from None
        except Exception:
            logger.exception("tool failed", extra={"tool": name})
            raise ToolError("internal MCP tool error") from None
    logger.info("tool completed", extra={"tool": name})
    return result


async def _execute_resource[ModelT: BaseModel](
    name: str,
    operation: Callable[[], Awaitable[ModelT]],
) -> ModelT:
    try:
        result = await operation()
    except McpServiceError as exc:
        logger.warning(
            "resource read failed",
            extra={"resource": name, "error_type": type(exc).__name__},
        )
        raise RuntimeError(str(exc)) from None
    except Exception:
        logger.exception("resource read failed", extra={"resource": name})
        raise RuntimeError("internal MCP resource error") from None
    logger.info("resource read completed", extra={"resource": name})
    return result
