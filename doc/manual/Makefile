SIM_ROOT=../../
include $(SIM_ROOT)/common/Makefile.common

sniper-manual.pdf_SOURCE_FILES=

PDFLATEX_BIN=/usr/bin/pdflatex
GNUPLOT_BIN=/usr/bin/gnuplot
EPSTOPDF_BIN=/usr/bin/epstopdf
LATEX_XCOLOR=/usr/share/texmf/tex/latex/xcolor/xcolor.sty
LATEX_ENUMITEM=$(wildcard /usr/share/texmf-texlive/tex/latex/enumitem/enumitem.sty /usr/share/texlive/texmf-dist/tex/latex/enumitem/enumitem.sty)
REQ_FONTS=
DEPENDENCIES=$(PDFLATEX_BIN) $(GNUPLOT_BIN) $(EPSTOPDF_BIN) $(LATEX_XCOLOR) $(LATEX_ENUMITEM) $(REQ_FONTS)
AUTOGEN_FILES=sim_api_doc.h hooks.h manual-cpi-fft.eps manual-cpi-fft.pdf
TARGET=sniper-manual.pdf

.PHONY: pdf clean

pdf: $(TARGET)

sim_api_doc.h: ../../include/sim_api.h
	./gen_sim_api.sh

hooks.h: ../../common/system/hooks_manager.h
	./gen_hooks.sh

manual-cpi-fft.eps: manual-cpi-fft.input
	gnuplot manual-cpi-fft.input
manual-cpi-fft.pdf: manual-cpi-fft.eps
	epstopdf --outfile=manual-cpi-fft.pdf manual-cpi-fft.eps

.SECONDEXPANSION:

%.pdf: %.tex $$($$@_SOURCE_FILES) $(DEPENDENCIES) $(AUTOGEN_FILES)
ifeq ($(SHOW_COMPILE),)
	@echo '[LATEX ]' $(subst $(abspath $(SIM_ROOT))/,,$(abspath $@))
	@pdflatex -interaction nonstopmode -halt-on-error ${*}.tex
	@echo '[BIBTEX]' $(subst $(abspath $(SIM_ROOT))/,,$(abspath $@))
	@bibtex ${*} || true
	@echo '[LATEX2]' $(subst $(abspath $(SIM_ROOT))/,,$(abspath $@))
	@pdflatex ${*}.tex
	@echo '[LATEX3]' $(subst $(abspath $(SIM_ROOT))/,,$(abspath $@))
	@pdflatex ${*}.tex
else
	pdflatex -interaction nonstopmode -halt-on-error ${*}.tex
	bibtex ${*} || true
	pdflatex ${*}.tex
	pdflatex ${*}.tex
endif

# pdflatex is needed for making the tex file into a pdf
$(PDFLATEX_BIN):
	@echo
	@echo "Error: please install pdflatex.  In Ubuntu, run 'sudo apt-get install texlive-latex-base'"
	@echo
	@false

$(EPSTOPDF_BIN):
	@echo
	@echo "Error: please install epstopdf.  In Ubuntu, run 'sudo apt-get install texlive-font-utils'"
	@echo
	@false

$(LATEX_XCOLOR):
	@echo
	@echo "Error: please install latex-xcolor.  In Ubuntu, run 'sudo apt-get install latex-xcolor'"
	@echo
	@false

$(LATEX_ENUMITEM):
	@echo
	@echo "Error: please install the latex extras.  In Ubuntu, run 'sudo apt-get install texlive-latex-extra'"
	@echo
	@false

$(GNUPLOT_BIN):
	@echo
	@echo "Error: please install gnuplot.  In Ubuntu, run 'sudo apt-get install gnuplot'"
	@echo
	@false

clean:
ifeq ($(SHOW_COMPILE),)
	@echo '[CLEAN ]' $(subst $(abspath $(SIM_ROOT))/,,$(abspath .))
	@rm -rf *.aux *.bbl *.blg *.log *.toc *.out $(TARGET) $(AUTOGEN_FILES)
else
	rm -rf *.aux *.bbl *.blg *.log *.toc *.out $(TARGET) $(AUTOGEN_FILES)
endif
