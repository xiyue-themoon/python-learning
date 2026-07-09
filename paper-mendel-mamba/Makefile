# Makefile — Mendel's Factor to Mamba's State paper
# Toolchain: xelatex (MiKTeX) + biber/bibtex
# Usage:
#   make          — build PDF (default)
#   make clean    — remove build artifacts
#   make watch    — auto-rebuild on .tex changes (needs inotify/powershell)

NAME := Ma_Mendel_Mamba_2026
SRC  := src/$(NAME)
OUT  := output
BLD  := build

LATEXMK := latexmk
PDFLATEX := xelatex
FLAGS := -xelatex -interaction=nonstopmode -output-directory=$(BLD)

.PHONY: all clean watch

all: $(OUT)/$(NAME).pdf

$(OUT)/$(NAME).pdf: $(SRC).tex src/references.bib | $(OUT) $(BLD)
	latexmk -xelatex -interaction=nonstopmode -output-directory=$(BLD) $(SRC).tex
	cp $(BLD)/$(NAME).pdf $(OUT)/$(NAME).pdf
	@echo ""
	@echo "=== BUILD COMPLETE ==="
	@echo "PDF: $(OUT)/$(NAME).pdf"

$(OUT):
	mkdir -p $(OUT)

$(BLD):
	mkdir -p $(BLD)

clean:
	rm -rf $(BLD)
	rm -f $(OUT)/$(NAME).pdf
	@echo "Cleaned."

watch:
	@echo "Watching $(SRC).tex for changes (Ctrl+C to stop)..."
	@while true; do \
		inotifywait -e modify $(SRC).tex 2>/dev/null || \
		powershell -Command " \
			while(1) { \
				$$t=[System.IO.File]::GetLastWriteTime('$(SRC).tex'); \
				if(($$t-[DateTime]::Now).TotalSeconds -le 2 -and ($$t-[DateTime]::Now).TotalSeconds -ge -2) { \
					break; \
				} \
				Start-Sleep -Milliseconds 500; \
			}" 2>/dev/null; \
		make; \
	done

verify: all
	/c/Users/ROG/miniconda3/envs/hermes/python.exe verify.py --src $(SRC).tex --keep
