VER=1

PREFIX=/usr/local

BINPROGS = \
	mkaurball

V_GEN = $(_v_GEN_$(V))
_v_GEN_ = $(_v_GEN_0)
_v_GEN_0 = @echo "  GEN     " $@;

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

smoketest:
	@for repo in core extra community multilib; \
		do echo testing $$repo; time ./compare.py $$repo >$$repo.log; \
	done

.PHONY: smoketest clean
