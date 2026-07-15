" Vim plugin setup for GhostCoder
" Define commands for Neovim user interaction

if exists("g:loaded_ghostcoder")
    finish
endif
let g:loaded_ghostcoder = 1

command! GhostEnable lua require('ghostcoder').enable()
command! GhostDisable lua require('ghostcoder').disable()
command! GhostStatus lua require('ghostcoder').status()
command! GhostHover lua require('ghostcoder').hover()

" Initialize when Neovim starts up
lua require('ghostcoder').setup()
