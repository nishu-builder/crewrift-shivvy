# Shivvy CrewRift player image.
#
# Our source lives in src/ (shivvy.nim + the shivvy/ support modules). The
# CrewRift engine (game sim + sprite protocol contract) and the bitworld
# libraries are *build dependencies*: we fetch coworld-crewrift at a pinned
# commit and let nimby resolve the Nim deps from its nimby.lock. We overlay
# our player source into the engine tree at players/shivvy/ and compile.
#
# Bump CREWRIFT_ENGINE_REF when adopting a new engine/protocol version, then
# re-run scripts/build.sh and a local scrimmage before submitting.

FROM debian:bookworm-slim AS build

ARG CREWRIFT_ENGINE_REF=716fc42b2e375cc6c051b28e53057c2c7e43c0b8

RUN apt-get update && \
  apt-get install -y --no-install-recommends \
    build-essential ca-certificates curl git && \
  rm -rf /var/lib/apt/lists/*

# nimby pins the Nim toolchain and resolves the engine's locked Nim deps.
RUN if [ "$(dpkg --print-architecture)" = "amd64" ]; then \
    curl -fsSL -o /usr/local/bin/nimby \
      https://github.com/treeform/nimby/releases/download/0.1.26/nimby-Linux-X64; \
  elif [ "$(dpkg --print-architecture)" = "arm64" ]; then \
    curl -fsSL -o /usr/local/bin/nimby \
      https://github.com/treeform/nimby/releases/download/0.1.26/nimby-Linux-ARM64; \
  else echo "unsupported arch: $(dpkg --print-architecture)" && exit 1; fi && \
  chmod +x /usr/local/bin/nimby && \
  nimby use 2.2.4
ENV PATH="/root/.nimby/nim/bin:$PATH"

WORKDIR /workspace
RUN git clone https://github.com/Metta-AI/coworld-crewrift.git crewrift && \
  cd crewrift && git checkout "${CREWRIFT_ENGINE_REF}"

WORKDIR /workspace/crewrift
RUN nimby --global sync nimby.lock

# Overlay our player source onto the pinned engine and compile.
COPY src/shivvy.nim players/shivvy/shivvy.nim
COPY src/shivvy/ players/shivvy/shivvy/
RUN nim c \
  -d:release \
  -d:botHeadless \
  -d:useMalloc \
  --opt:speed \
  --stackTrace:on \
  --nimcache:/tmp/shivvy-nimcache \
  --out:shivvy \
  players/shivvy/shivvy.nim

FROM debian:bookworm-slim
RUN apt-get update && \
  apt-get install -y --no-install-recommends ca-certificates libcurl4 && \
  rm -rf /var/lib/apt/lists/*
# The bot setCurrentDir's into its build-time game dir (/workspace/crewrift) on
# startup; create it so the headless binary runs (it reads map/walkability from
# the sprite stream, not from disk, so the dir can be empty).
WORKDIR /workspace/crewrift
COPY --from=build /workspace/crewrift/shivvy /bin/shivvy
CMD ["/bin/shivvy"]
