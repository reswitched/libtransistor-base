# llvm programs

# On MacOS, brew refuses to install clang5/llvm5 in a global place. As a result,
# they have to muck around with changing the path, which sucks.
# Let's make their lives easier by asking brew where LLVM_CONFIG is.
ifeq ($(shell uname -s),Darwin)
    ifeq ($(shell brew --prefix llvm),)
        $(error need llvm installed via brew)
    else
        LLVM_CONFIG := $(shell brew --prefix llvm)/bin/llvm-config
    endif
else
    LLVM_CONFIG := llvm-config$(LLVM_POSTFIX)
endif

LLVM_BINDIR := $(shell $(LLVM_CONFIG) --bindir)
ifeq ($(LLVM_BINDIR),)
  $(error llvm-config needs to be installed)
endif

LD := $(LLVM_BINDIR)/ld.lld
CC := $(LLVM_BINDIR)/clang
CXX := $(LLVM_BINDIR)/clang++
AS := $(LLVM_BINDIR)/llvm-mc
AR := $(LLVM_BINDIR)/llvm-ar
RANLIB := $(LLVM_BINDIR)/llvm-ranlib

# interpreters
PYTHON3 := python3
MEPHISTO := ctu
RUBY := ruby

SYS_INCLUDES := -isystem $(LIBTRANSISTOR_HOME)/include/
CPP_INCLUDES := -isystem $(LIBTRANSISTOR_HOME)/include/c++/v1/

# linker flags for building main binary
#   -Bsymbolic: bind symbols locally
#   --shared: build a shared object
LD_FLAGS := -Bsymbolic \
	--shared \
	--no-gc-sections \
	--eh-frame-hdr \
	--no-undefined \
	-T $(LIBTRANSISTOR_HOME)/link.T \
	-L $(LIBTRANSISTOR_HOME)/lib/

# linker flags for building shared libraries
#   --shared: build a shared object
#   -Bdynamic: link against shared libraries
LD_SHARED_LIBRARY_FLAGS := --shared \
	--no-gc-sections \
	--eh-frame-hdr \
	-T $(LIBTRANSISTOR_HOME)/link.T \
	-L $(LIBTRANSISTOR_HOME)/lib/ \
	-Bdynamic

CC_FLAGS := -g -fPIC -fexceptions -fuse-ld=lld -fstack-protector-strong -O3 -mtune=cortex-a53 -target aarch64-none-linux-gnu -nostdlib -nostdlibinc $(SYS_INCLUDES) -D__SWITCH__=1 -Wno-unused-command-line-argument
CXX_FLAGS := $(CPP_INCLUDES) $(CC_FLAGS) -std=c++17 -stdlib=libc++ -nodefaultlibs -nostdinc++
AR_FLAGS := rcs
AS_FLAGS := -arch=aarch64 -triple aarch64-none-switch

# for compatiblity
CFLAGS := $(CC_FLAGS)
CXXFLAGS := $(CXX_FLAGS)

LIB_DEP_COMPILER_RT_BUILTINS := $(LIBTRANSISTOR_HOME)/lib/libclang_rt.builtins-aarch64.a
LIB_DEP_NEWLIB_LIBC := $(LIBTRANSISTOR_HOME)/lib/libc.a
LIB_DEP_NEWLIB_LIBM := $(LIBTRANSISTOR_HOME)/lib/libm.a
LIB_DEP_PTHREAD := $(LIBTRANSISTOR_HOME)/lib/libpthread.a
LIB_DEP_LIBLZMA := $(LIBTRANSISTOR_HOME)/lib/liblzma.a
LIB_DEP_LIBCXX := $(LIBTRANSISTOR_HOME)/lib/libc++.a
LIB_DEP_LIBCXXABI := $(LIBTRANSISTOR_HOME)/lib/libc++abi.a
LIB_DEP_LIBUNWIND := $(LIBTRANSISTOR_HOME)/lib/libunwind.a
CXX_LIB_DEPS := $(LIB_DEP_LIBCXX) $(LIB_DEP_LIBCXXABI) $(LIB_DEP_LIBUNWIND)
LIBTRANSISTOR_COMMON_LIB_DEPS := $(LIB_DEP_NEWLIB_LIBC) $(LIB_DEP_NEWLIB_LIBM) $(LIB_DEP_COMPILER_RT_BUILTINS) $(LIB_DEP_PTHREAD) $(LIB_DEP_LIBLZMA) $(CXX_LIB_DEPS) $(LIBTRANSISTOR_HOME)/link.T
LIBTRANSISTOR_COMMON_LIBS := $(LIBTRANSISTOR_COMMON_LIB_DEPS) # for older Makefiles
LIBTRANSISTOR_NRO_DEP := $(LIBTRANSISTOR_HOME)/lib/libtransistor.nro.a
LIBTRANSISTOR_NSO_DEP := $(LIBTRANSISTOR_HOME)/lib/libtransistor.nso.a
LIBTRANSISTOR_NRO_LIB := $(LIBTRANSISTOR_NRO_DEP)
LIBTRANSISTOR_NSO_LIB := $(LIBTRANSISTOR_NSO_DEP)
LIBTRANSISTOR_NRO_DEPS := $(LIBTRANSISTOR_HOME)/lib/libtransistor.nro.a $(LIBTRANSISTOR_COMMON_LIB_DEPS)
LIBTRANSISTOR_NSO_DEPS := $(LIBTRANSISTOR_HOME)/lib/libtransistor.nso.a $(LIBTRANSISTOR_COMMON_LIB_DEPS)

# these are libraries that libtransistor depends on, and that must be statically linked.
# any other libraries may be dynamically linked.
#   -Bstatic: do not link against shared libraries
#   -Bdynamic: link against shared libraries
LIBTRANSISTOR_EXECUTABLE_LDFLAGS := -Bstatic \
	-lc -lm -lclang_rt.builtins-aarch64 -lpthread -llzma -lc++ -lc++abi -lunwind \
	-Bdynamic

LIBTRANSISTOR_NRO_LDFLAGS := --whole-archive -ltransistor.nro --no-whole-archive $(LIBTRANSISTOR_EXECUTABLE_LDFLAGS)
LIBTRANSISTOR_NSO_LDFLAGS := --whole-archive -ltransistor.nso --no-whole-archive $(LIBTRANSISTOR_EXECUTABLE_LDFLAGS)
LIBTRANSISTOR_LIB_LDFLAGS := -lc -lclang_rt.builtins-aarch64 -lc++ -lc++abi -lunwind

%.nro: %.nro.so
	$(PYTHON3) $(LIBTRANSISTOR_HOME)/tools/elf2nxo.py $< $@ nro

%.nso: %.nso.so
	$(PYTHON3) $(LIBTRANSISTOR_HOME)/tools/elf2nxo.py $< $@ nso
