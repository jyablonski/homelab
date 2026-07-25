class McpServiceError(Exception):
    pass


class DownstreamUnavailableError(McpServiceError):
    pass


class DownstreamRejectedError(McpServiceError):
    pass


class DownstreamResponseError(McpServiceError):
    pass


class ResourceNotFoundError(McpServiceError):
    pass
