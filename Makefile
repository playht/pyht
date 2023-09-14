PROTO_SRC_DIR := protos
PROTO_DEST_DIR := pyht/protos
PROTO_SRCS := $(wildcard $(PROTO_SRC_DIR)/*.proto)

PROTO_OUTS := $(patsubst $(PROTO_SRC_DIR)/%.proto,$(PROTO_DEST_DIR)/%_pb2.py,$(PROTO_SRCS))
PROTO_GRPC_OUTS := $(patsubst $(PROTO_SRC_DIR)/%.proto,$(PROTO_DEST_DIR)/%_pb2_grpc.py,$(PROTO_SRCS))
PROTO_TYPES := $(patsubst $(PROTO_SRC_DIR)/%.proto,$(PROTO_DEST_DIR)/%_pb2.pyi,$(PROTO_SRCS))

ifeq ($(shell uname -s),Darwin)
    SED_INPLACE = -i ''
else
    SED_INPLACE = -i
endif

all: protos

protos: $(PROTO_OUTS) $(PROTO_GRPC_OUTS) $(PROTO_TYPES)

$(PROTO_DEST_DIR)/%_pb2.py: $(PROTO_SRC_DIR)/%.proto
	python -m grpc_tools.protoc -I$(PROTO_SRC_DIR) --python_out=$(PROTO_DEST_DIR) $<

$(PROTO_DEST_DIR)/%_pb2_grpc.py: $(PROTO_SRC_DIR)/%.proto
	python -m grpc_tools.protoc -I$(PROTO_SRC_DIR) --grpc_python_out=$(PROTO_DEST_DIR) $<
	sed $(SED_INPLACE) 's/import \([a-zA-Z0-9_]*_pb2\)/from . import \1/g' $@

$(PROTO_DEST_DIR)/%_pb2.pyi: $(PROTO_SRC_DIR)/%.proto
	python -m grpc_tools.protoc -I$(PROTO_SRC_DIR) --pyi_out=$(PROTO_DEST_DIR) $<

clean:
	rm -f $(PROTO_DEST_DIR)/*_pb2.py $(PROTO_DEST_DIR)/*_pb2_grpc.py $(PROTO_DEST_DIR)/*_pb2.pyi

distclean: clean
	rm -rf dist/

.PHONY: all protos clean distclean
