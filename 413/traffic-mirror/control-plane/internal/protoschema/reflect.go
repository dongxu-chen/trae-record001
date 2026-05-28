package protoschema

import (
	"fmt"

	"google.golang.org/protobuf/proto"
	"google.golang.org/protobuf/reflect/protodesc"
	"google.golang.org/protobuf/reflect/protoreflect"
	"google.golang.org/protobuf/types/descriptorpb"
	"google.golang.org/protobuf/types/dynamicpb"

	"github.com/traffic-mirror/control-plane/pkg/types"
)

type Resolver struct {
	schemas map[string]protoreflect.MessageDescriptor
}

func NewResolver() *Resolver {
	return &Resolver{
		schemas: make(map[string]protoreflect.MessageDescriptor),
	}
}

func (r *Resolver) Register(messageType string, fileDescriptorBytes []byte) error {
	fdSet := &descriptorpb.FileDescriptorSet{}
	if err := proto.Unmarshal(fileDescriptorBytes, fdSet); err != nil {
		return fmt.Errorf("unmarshal file descriptor set: %w", err)
	}

	files, err := protodesc.NewFiles(fdSet)
	if err != nil {
		return fmt.Errorf("create proto files: %w", err)
	}

	fd, err := files.FindFileByPath(fdSet.File[0].GetName())
	if err != nil {
		return fmt.Errorf("find file: %w", err)
	}

	msgDesc := fd.Messages().ByName(protoreflect.Name(messageType))
	if msgDesc == nil {
		fullName := protoreflect.FullName(messageType)
		msgDesc = fd.Messages().ByName(fullName.Name())
	}
	if msgDesc == nil {
		msgDesc = findMessageRecursive(fd, messageType)
	}
	if msgDesc == nil {
		return fmt.Errorf("message %s not found in file descriptor", messageType)
	}

	r.schemas[messageType] = msgDesc
	return nil
}

func (r *Resolver) Unregister(messageType string) {
	delete(r.schemas, messageType)
}

func (r *Resolver) Has(messageType string) bool {
	_, ok := r.schemas[messageType]
	return ok
}

func (r *Resolver) MessageDescriptor(messageType string) (protoreflect.MessageDescriptor, bool) {
	md, ok := r.schemas[messageType]
	return md, ok
}

func findMessageRecursive(fd protoreflect.FileDescriptor, messageType string) protoreflect.MessageDescriptor {
	messages := fd.Messages()
	for i := 0; i < messages.Len(); i++ {
		m := messages.Get(i)
		if string(m.FullName()) == messageType {
			return m
		}
	}
	for i := 0; i < messages.Len(); i++ {
		m := messages.Get(i)
		if sub := findNestedMessage(m, messageType); sub != nil {
			return sub
		}
	}
	return nil
}

func findNestedMessage(m protoreflect.MessageDescriptor, messageType string) protoreflect.MessageDescriptor {
	nested := m.Messages()
	for i := 0; i < nested.Len(); i++ {
		nm := nested.Get(i)
		if string(nm.FullName()) == messageType {
			return nm
		}
		if sub := findNestedMessage(nm, messageType); sub != nil {
			return sub
		}
	}
	return nil
}

func (r *Resolver) Compare(messageType string, prodBody, testBody []byte) ([]*types.ProtoFieldDiff, error) {
	md, ok := r.schemas[messageType]
	if !ok {
		return nil, fmt.Errorf("message type %s not registered", messageType)
	}

	prodMsg := dynamicpb.NewMessage(md)
	if err := proto.Unmarshal(prodBody, prodMsg); err != nil {
		return nil, fmt.Errorf("unmarshal production body: %w", err)
	}

	testMsg := dynamicpb.NewMessage(md)
	if err := proto.Unmarshal(testBody, testMsg); err != nil {
		return nil, fmt.Errorf("unmarshal test body: %w", err)
	}

	var diffs []*types.ProtoFieldDiff
	for i := 0; i < md.Fields().Len(); i++ {
		field := md.Fields().Get(i)
		prodVal := prodMsg.Get(field)
		testVal := testMsg.Get(field)

		prodStr := formatValue(field, prodVal)
		testStr := formatValue(field, testVal)

		if prodStr != testStr {
			severity := "warning"
			if field.IsList() || field.IsMap() || field.Kind() == protoreflect.MessageKind {
				severity = "critical"
			}

			diffs = append(diffs, &types.ProtoFieldDiff{
				FieldNumber: int32(field.Number()),
				FieldName:   string(field.Name()),
				WireType:    int32(protoWireType(field)),
				ProdVal:     prodStr,
				TestVal:     testStr,
				Severity:    severity,
			})
		}
	}

	return diffs, nil
}

func formatValue(field protoreflect.FieldDescriptor, val protoreflect.Value) string {
	if field.IsList() {
		return fmt.Sprintf("list(%v)", val)
	}
	if field.IsMap() {
		return fmt.Sprintf("map(%v)", val)
	}
	return fmt.Sprintf("%v", val.Interface())
}

func protoWireType(field protoreflect.FieldDescriptor) int32 {
	switch field.Kind() {
	case protoreflect.BoolKind, protoreflect.Int32Kind, protoreflect.Int64Kind,
		protoreflect.Uint32Kind, protoreflect.Uint64Kind,
		protoreflect.Sint32Kind, protoreflect.Sint64Kind:
		return 0
	case protoreflect.Fixed64Kind, protoreflect.Sfixed64Kind, protoreflect.DoubleKind:
		return 1
	case protoreflect.StringKind, protoreflect.BytesKind, protoreflect.MessageKind:
		return 2
	case protoreflect.Fixed32Kind, protoreflect.Sfixed32Kind, protoreflect.FloatKind:
		return 5
	default:
		return -1
	}
}
