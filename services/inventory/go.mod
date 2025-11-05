module github.com/bookstore/inventory

go 1.22

require (
	github.com/lib/pq v1.10.9
	github.com/rabbitmq/amqp091-go v1.9.0
	google.golang.org/grpc v1.67.0
	google.golang.org/protobuf v1.34.2
)

require (
	golang.org/x/net v0.28.0 // indirect
	golang.org/x/sys v0.24.0 // indirect
	golang.org/x/text v0.17.0 // indirect
	google.golang.org/genproto/googleapis/rpc v0.0.0-20240814211410-ddb44dafa142 // indirect
)

// Local contract - path is relative to the Docker build context
replace github.com/bookstore/contracts/gen/go/inventory => /contracts/gen/go/inventory
