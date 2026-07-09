# Makefile — 论文编译管线 (Cloud/Linux 版)
# Toolchain: xelatex + biber + pdftotext
# Usage:
#   make          — build PDF (default)
#   make verify   — build + CI 校验
#   make clean    — remove build artifacts
#   make watch    — auto-rebuild on .tex changes (needs inotifywait)

NAME := Ma_Mendel_Mamba_2026
SRC  := src/$(NAME)
OUT  := output
BLD  := build

.PHONY: all clean watch verify

all: $(OUT)/$(NAME).pdf

$(OUT)/$(NAME).pdf: $(SRC).tex src/references.bib | $(OUT) $(BLD)
	xelatex -interaction=nonstopmode -output-directory=$(BLD) $(SRC).tex
	biber $(BLD)/$(NAME)
	xelatex -interaction=nonstopmode -output-directory=$(BLD) $(SRC).tex
	xelatex -interaction=nonstopmode -output-directory=$(BLD) $(SRC).tex
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
		inotifywait -e modify $(SRC).tex 2>/dev/null; \
		make; \
	done

verify: all
	python3 verify.py --src $(SRC).tex --keep
