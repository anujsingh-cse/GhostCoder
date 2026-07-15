-- Neovim socket communication for GhostCoder
local M = {}

local uv = vim.uv or vim.loop
local client = nil
local is_connected = false
local reconnect_timer = nil

local socket_path = vim.fn.expand("~/.ghostcoder/ghostcoder.sock")
local fallback_ip = "127.0.0.1"
local fallback_port = 48673

local function on_read(err, chunk)
  if err then
    M.disconnect()
    return
  end
  if chunk then
    -- Process stream data
    for line in string.gmatch(chunk, "[^\r\n]+") do
      local ok, msg = pcall(vim.json.decode, line)
      if ok and msg then
        if msg.type == "suggestion" then
          -- Trigger decoration / hint rendering
          require("ghostcoder.hints").show_hint(msg)
        elseif msg.type == "clear_suggestion" then
          require("ghostcoder.hints").clear_hint()
        end
      end
    end
  else
    M.disconnect()
  end
end

function M.connect(on_status_change)
  if is_connected then return end

  -- Try Unix socket first
  local pipe = uv.new_pipe(false)
  client = pipe

  pipe:connect(socket_path, function(err)
    if err then
      -- Fallback to TCP
      pipe:close()
      
      local tcp = uv.new_tcp()
      client = tcp
      
      tcp:connect(fallback_ip, fallback_port, function(tcp_err)
        if tcp_err then
          tcp:close()
          is_connected = false
          if on_status_change then on_status_change(false) end
          return
        end
        
        is_connected = true
        if on_status_change then on_status_change(true) end
        tcp:read_start(on_read)
      end)
      return
    end

    is_connected = true
    if on_status_change then on_status_change(true) end
    pipe:read_start(on_read)
  end)
end

function M.send(data)
  if not is_connected or not client then return end
  local ok, payload = pcall(vim.json.encode, data)
  if ok then
    client:write(payload .. "\n")
  end
end

function M.disconnect()
  if client then
    pcall(client.read_stop, client)
    pcall(client.close, client)
    client = nil
  end
  is_connected = false
end

function M.get_status()
  return is_connected and "Connected" or "Disconnected"
end

return M
