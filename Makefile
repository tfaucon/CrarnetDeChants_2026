JOBNAME = main
BUILDDIR = build
PDFLATEX = pdflatex -output-directory=$(BUILDDIR) -interaction=nonstopmode

.PHONY: all clean view

all: $(BUILDDIR)/$(JOBNAME).pdf

$(BUILDDIR)/$(JOBNAME).pdf: main.tex preamble/*.tex frontmatter/*.tex songs/*.tex backmatter/*.tex
	@mkdir -p $(BUILDDIR)
	$(PDFLATEX) $(JOBNAME).tex
	texlua songidx.lua $(BUILDDIR)/main_title.sxd $(BUILDDIR)/main_title.sbx
	$(PDFLATEX) $(JOBNAME).tex
	texlua songidx.lua $(BUILDDIR)/main_title.sxd $(BUILDDIR)/main_title.sbx
	$(PDFLATEX) $(JOBNAME).tex

clean:
	rm -rf $(BUILDDIR)

view: all
	xdg-open $(BUILDDIR)/$(JOBNAME).pdf &
