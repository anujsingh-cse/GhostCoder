-- Main entry point for GhostCoder Neovim plugin
local M = {}

local daemon = require("ghostcoder.daemon")
local hints = require("ghostcoder.hints")

local enabled = true

function M.setup(opts)
  opts = opts or {}
  
  -- Initial connection
  if enabled then
    daemon.connect(function(connected)
      if connected then
        vim.notify("GhostCoder: Connected to background daemon.", vim.log.levels.INFO)
      end
    end)
  end

  -- Default keymaps
  vim.keymap.set("n", "<M-a>", M.apply, { desc = "GhostCoder: Accept original suggestion" })
  vim.keymap.set("n", "<M-s>", M.apply_skeptic, { desc = "GhostCoder: Accept Skeptic's improved version" })
  vim.keymap.set("n", "<M-d>", M.dismiss, { desc = "GhostCoder: Dismiss both" })

  -- Autocommands to watch files & update daemon
  local group = vim.api.nvim_create_augroup("GhostCoderGroup", { clear = true })

  vim.api.nvim_create_autocmd({ "TextChanged", "TextChangedI" }, {
    group = group,
    pattern = "*",
    callback = function()
      if not enabled then return end
      local buf = vim.api.nvim_get_current_buf()
      local filepath = vim.api.nvim_buf_get_name(buf)
      if filepath ~= "" and vim.bo[buf].buftype == "" then
        local lines = vim.api.nvim_buf_get_lines(buf, 0, -1, false)
        local content = table.concat(lines, "\n")
        daemon.send({
          type = "editor_change",
          file = filepath,
          content = content
        })
      end
    end
  })

  vim.api.nvim_create_autocmd({ "BufWritePost" }, {
    group = group,
    pattern = "*",
    callback = function()
      if not enabled then return end
      local buf = vim.api.nvim_get_current_buf()
      local filepath = vim.api.nvim_buf_get_name(buf)
      if filepath ~= "" then
        daemon.send({
          type = "action",
          action = "save",
          file = filepath
        })
      end
    end
  })

  vim.api.nvim_create_autocmd({ "CursorHold", "CursorHoldI" }, {
    group = group,
    pattern = "*",
    callback = function()
      if not enabled then return end
      -- Clean suggestion if cursor moved away from lines?
      -- For now, keep it simple.
    end
  })
end

function M.enable()
  enabled = true
  daemon.connect(function(connected)
    if connected then
      vim.notify("GhostCoder enabled.")
    else
      vim.notify("GhostCoder: Could not connect to daemon.", vim.log.levels.ERROR)
    end
  end)
end

function M.disable()
  enabled = false
  daemon.disconnect()
  hints.clear_hint()
  vim.notify("GhostCoder disabled.")
end

function M.status()
  local status = daemon.get_status()
  vim.notify("GhostCoder Status: " .. status)
end

function M.hover()
  hints.show_hover()
end

function M.apply()
  hints.apply_suggestion()
end

function M.apply_skeptic()
  hints.apply_skeptic_suggestion()
end

function M.dismiss()
  hints.dismiss_suggestion()
end

return M
