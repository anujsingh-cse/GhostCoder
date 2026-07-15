-- Neovim virtual text rendering and floating windows for GhostCoder
local M = {}

local ns_id = vim.api.nvim_create_namespace("ghostcoder_hints")
local current_hint = nil
local active_line = nil

-- Define default highlights
vim.api.nvim_set_hl(0, "GhostCoderVirtualText", { link = "Comment" })
vim.api.nvim_set_hl(0, "GhostCoderFloatBorder", { link = "FloatBorder" })

function M.show_hint(suggestion)
  current_hint = suggestion
  local hint_text = suggestion.hint or ""
  local agent = suggestion.agent or "GhostCoder"
  
  local buf = vim.api.nvim_get_current_buf()
  local cursor_pos = vim.api.nvim_win_get_cursor(0)
  local line_num = cursor_pos[1] - 1  -- 0-indexed for API
  active_line = line_num
  
  -- Clear previous virtual text first
  vim.api.nvim_buf_clear_namespace(buf, ns_id, 0, -1)
  
  local vt_message = ""
  if suggestion.skeptic_blocked then
    local flaws = "Blocked by Skeptic"
    if suggestion.challenges and #suggestion.challenges > 0 then
      local flaw_list = {}
      for _, c in ipairs(suggestion.challenges) do
        table.insert(flaw_list, c.flaw)
      end
      flaws = "Blocked: " .. table.concat(flaw_list, ", ")
    end
    vt_message = string.format(" 👻 [Skeptic Blocked]: %s", flaws)
  else
    -- Clean up hint to fit in a single line for virtual text
    local clean_hint = hint_text:gsub("\n", " ")
    if #clean_hint > 60 then
      clean_hint = clean_hint:sub(1, 57) .. "..."
    end
    vt_message = string.format(" 👻 [%s]: %s", agent, clean_hint)
  end
  
  -- Add new virtual text
  vim.api.nvim_buf_set_extmark(buf, ns_id, line_num, 0, {
    virt_text = { { vt_message, "GhostCoderVirtualText" } },
    virt_text_pos = "eol",
  })
end

function M.clear_hint()
  current_hint = nil
  active_line = nil
  local buf = vim.api.nvim_get_current_buf()
  vim.api.nvim_buf_clear_namespace(buf, ns_id, 0, -1)
end

function M.apply_suggestion()
  if not current_hint or not current_hint.fix then
    vim.notify("GhostCoder: No fix available to apply.")
    return
  end
  local buf = vim.api.nvim_get_current_buf()
  if active_line then
    local fix_lines = {}
    for line in string.gmatch(current_hint.fix, "[^\r\n]+") do
      table.insert(fix_lines, line)
    end
    vim.api.nvim_buf_set_lines(buf, active_line, active_line + 1, false, fix_lines)
    M.clear_hint()
    require("ghostcoder.daemon").send({ type = "action", action = "apply" })
    vim.notify("GhostCoder: Suggestion applied!")
  end
end

function M.apply_skeptic_suggestion()
  if not current_hint or not current_hint.skeptic_fix then
    vim.notify("GhostCoder: No skeptic fix available to apply.")
    return
  end
  local buf = vim.api.nvim_get_current_buf()
  if active_line then
    local fix_lines = {}
    for line in string.gmatch(current_hint.skeptic_fix, "[^\r\n]+") do
      table.insert(fix_lines, line)
    end
    vim.api.nvim_buf_set_lines(buf, active_line, active_line + 1, false, fix_lines)
    M.clear_hint()
    require("ghostcoder.daemon").send({ type = "action", action = "apply_skeptic" })
    vim.notify("GhostCoder: Skeptic's improved suggestion applied!")
  end
end

function M.dismiss_suggestion()
  M.clear_hint()
  require("ghostcoder.daemon").send({ type = "action", action = "dismiss" })
  vim.notify("GhostCoder: Suggestion dismissed.")
end

function M.show_hover()
  if not current_hint then
    vim.notify("GhostCoder: No active suggestion.")
    return
  end
  
  local agent = current_hint.agent or "GhostCoder"
  
  local content = {}
  if current_hint.skeptic_blocked then
    table.insert(content, "👻 GhostCoder [Skeptic Blocked]")
    table.insert(content, "Original suggestion was blocked due to critical flaws.")
  else
    table.insert(content, string.format("👻 GhostCoder Suggestion (%s)", agent))
    table.insert(content, string.rep("─", 40))
    local hint_text = current_hint.hint or ""
    for line in string.gmatch(hint_text, "[^\r\n]+") do
      table.insert(content, line)
    end
  end
  
  if current_hint.challenges and #current_hint.challenges > 0 then
    table.insert(content, "")
    table.insert(content, "Skeptic Challenges:")
    table.insert(content, string.rep("─", 40))
    for _, c in ipairs(current_hint.challenges) do
      table.insert(content, string.format("- [%s] %s", string.upper(c.severity), c.flaw))
      table.insert(content, string.format("  Scenario: %s", c.scenario))
      table.insert(content, string.format("  Proposed Fix: %s", c.fix))
    end
  end
  
  table.insert(content, "")
  if current_hint.skeptic_blocked then
    table.insert(content, "Press Alt+S to apply Skeptic's improved version, or Alt+D to dismiss.")
  else
    table.insert(content, "Press Alt+A to apply original recommendation, Alt+S to apply Skeptic's version, or Alt+D to dismiss.")
  end
  
  -- Set up floating buffer
  local buf = vim.api.nvim_create_buf(false, true)
  vim.api.nvim_buf_set_lines(buf, 0, -1, false, content)
  
  -- Window layout
  local width = 80
  local height = #content
  local row = 1
  local col = 1
  
  local opts = {
    relative = "cursor",
    row = row,
    col = col,
    width = width,
    height = height,
    style = "minimal",
    border = "rounded",
  }
  
  local win = vim.api.nvim_open_win(buf, true, opts)
  
  -- Auto-close hover window when cursor moves
  vim.api.nvim_create_autocmd({ "CursorMoved", "InsertEnter" }, {
    buffer = buf,
    once = true,
    callback = function()
      if vim.api.nvim_win_is_valid(win) then
        vim.api.nvim_win_close(win, true)
      end
    end
  })
end

return M
