if exists("did_load_filetypes")
	finish
endif

augroup filetypedetect
	au! BufRead,BufNewFile *.mcproto	setfiletype mcproto
	au! BufRead,BufNewFile *.mcp		setfiletype mcproto
augroup END

