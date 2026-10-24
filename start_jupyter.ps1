# Start JupyterLab with fixed token for MCP integration
# This script starts JupyterLab configured to work with Antigravity's MCP jupyter server

$TOKEN = "artour_jupyter_token"
$PORT = 8888

Write-Host "Starting JupyterLab on port $PORT..." -ForegroundColor Cyan
Write-Host "Token: $TOKEN" -ForegroundColor Yellow
Write-Host "URL: http://localhost:$PORT/lab?token=$TOKEN" -ForegroundColor Green
Write-Host ""
Write-Host "After JupyterLab starts, restart AI Agent to enable MCP tools." -ForegroundColor Magenta

jupyter lab --port $PORT --IdentityProvider.token $TOKEN --no-browser
