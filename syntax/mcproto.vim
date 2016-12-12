" Vim syntax file
" Language: mcproto
" Maintainer: Eric Chai <electromatter@gmail.com>
" Latest Revision: 11 Dec 2016

" if some other script is the current syntax, then abort
if exists("b:current_syntax")
	finish
endif

syn match mcpComment "#.*$" contains=mcpTodo

syn region mcpString start='"' skip='\\"' end='"'
syn region mcpNamespace start='{' end='}' fold transparent contains=ALL

syn keyword mcpType unsigned signed float double
syn keyword mcpType bool byte ubyte short ushort int uint long ulong
syn keyword mcpType varint varlong
syn keyword mcpType bytes bytes_eof string uuid uuid_string
syn keyword mcpType array bool_optional
syn keyword mcpType angle position metadata slot nbt

syn keyword mcpKeyword namespace type variant
syn keyword mcpTodo contained TODO FIXME

let b:current_syntax = "mcproto"

hi link mcpKeyword	Keyword
hi link mcpType		Type
hi link mcpTodo		Todo
hi link mcpComment	Comment
hi link mcpString	Constant

