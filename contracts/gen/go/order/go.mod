module github.com/bookstore/contracts/gen/go/order

go 1.23.0

replace github.com/bookstore/contracts/gen/go/common => ../common

require (
	github.com/bookstore/contracts/gen/go/common v0.0.0-00010101000000-000000000000
	google.golang.org/grpc v1.60.1
	google.golang.org/protobuf v1.36.10
)

require (
	github.com/golang/protobuf v1.5.3 // indirect
	golang.org/x/net v0.42.0 // indirect
	golang.org/x/sys v0.34.0 // indirect
	golang.org/x/text v0.27.0 // indirect
	google.golang.org/genproto/googleapis/rpc v0.0.0-20250804133106-a7a43d27e69b // indirect
)
