PACKAGE=pkgbuild-introspection
VER=1

PREFIX=/usr/local

BINPROGS = \
	mkaurball

V_GEN = $(_v_GEN_$(V))
_v_GEN_ = $(_v_GEN_0)
_v_GEN_0 = @echo "  GEN     " $@;

V_TEST = $(_v_TEST_$(V))
_v_TEST = $(_v_TEST_0)
_v_TEST_0 = @echo "  TEST    " $@;

edit = $(V_GEN) m4 -P $@.in | sed 's/@VERSION@/$(VER)/g' >$@ && chmod go-w,+x $@

all: $(BINPROGS)

%: %.in pkgbuild_introspection
	$(edit)
	@bash -O extglob -n $@

install-bin: $(BINPROGS)
	install -dm755 $(DESTDIR)$(PREFIX)/bin
	install -m755 $(BINPROGS) $(DESTDIR)$(PREFIX)/bin

install: install-bin

clean:
	$(RM) $(BINPROGS)

TESTREPOS = \
	core \
	extra \
	community \
	multilib

smoketest: $(patsubst %, smoketest-%, $(TESTREPOS))
smoketest-%:
	$(V_TEST) test/smoketest $* >smoketest.$*.log

regtest: $(patsubst %, regtest-%, $(TESTREPOS))
regtest-%:
	$(V_TEST) test/regtest $* $(REFERENCE) >regtest.$*.log && rm regtest.$*.log

dist:
	git archive --format=tar --prefix=$(PACKAGE)-$(VER)/ $(VER) | gzip -9 >$(PACKAGE)-$(VER).tar.gz

upload: dist
	gpg --detach-sign $(PACKAGE)-$(VER).tar.gz
	scp $(PACKAGE)-$(VER).tar.gz $(PACKAGE)-$(VER).tar.gz.sig code.falconindy.com:archive/$(PACKAGE)/

.PHONY: regtest smoketest clean
