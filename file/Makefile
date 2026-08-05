CC      ?= gcc
CFLAGS  ?= -Wall -Wextra -O2 -std=c11
TARGET   = secauto
SRC      = security.c
PREFIX  ?= /opt/secauto

.PHONY: all clean install uninstall

all: $(TARGET)

$(TARGET): $(SRC)
	$(CC) $(CFLAGS) -o $@ $(SRC)

clean:
	rm -f $(TARGET)

# Install binary + python backend together so /proc/self/exe resolution
# finds automation/ right next to the binary.
install: all
	install -d $(DESTDIR)$(PREFIX)/automation
	install -m 0755 $(TARGET) $(DESTDIR)$(PREFIX)/$(TARGET)
	install -m 0644 automation/*.py $(DESTDIR)$(PREFIX)/automation/
	@echo "Installed to $(DESTDIR)$(PREFIX)"
	@echo "Run: $(DESTDIR)$(PREFIX)/$(TARGET)"

# Remove only the files we installed. rmdir (not rm -rf) leaves a shared
# prefix like /usr/local or $HOME intact if it still holds other files.
uninstall:
	rm -f $(DESTDIR)$(PREFIX)/$(TARGET)
	rm -f $(DESTDIR)$(PREFIX)/automation/*.py
	-rmdir $(DESTDIR)$(PREFIX)/automation
	-rmdir $(DESTDIR)$(PREFIX)
