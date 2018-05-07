# libtransistor-base
[![Build Status](https://travis-ci.org/reswitched/libtransistor-base.svg?branch=master)](https://travis-ci.org/reswitched/libtransistor-base) [![Chat on Discord](https://img.shields.io/badge/chat-Discord-brightgreen.svg)](https://discordapp.com/invite/ZdqEhed)

This is a collection of base libraries required to build libtransistor. In general,
the version numbers in this repository should match those in the main libtransistor
repository.

## Building

First, clone the repo with

```
git clone --recursive https://github.com/reswitched/libtransistor-base
```

You will need clang and lld >=5.0.0.

Running `make` should build all the libraries and install them to `dist/`. To build libtransistor, you will have to first copy this `dist/` directory to your libtransistor source root.

See [the main libtransistor repository](https://github.com/reswitched/libtransistor) for additional notes on packages you may have to install for your specific distro.
