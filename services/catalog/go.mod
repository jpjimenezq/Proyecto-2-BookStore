module github.com/bookstore/services/catalog

go 1.24.0

replace (
	github.com/bookstore/contracts/gen/go/catalog => ../../contracts/gen/go/catalog
	github.com/bookstore/contracts/gen/go/common => ../../contracts/gen/go/common
	github.com/bookstore/contracts/gen/go/inventory => ../../contracts/gen/go/inventory
)

require (
	github.com/bookstore/contracts/gen/go/catalog v0.0.0-00010101000000-000000000000
	github.com/bookstore/contracts/gen/go/common v0.0.0-00010101000000-000000000000
	github.com/bookstore/contracts/gen/go/inventory v0.0.0-00010101000000-000000000000
	github.com/google/uuid v1.6.0
	github.com/prometheus/client_golang v1.18.0
	github.com/rabbitmq/amqp091-go v1.9.0
	github.com/stretchr/testify v1.8.4
	go.uber.org/zap v1.26.0
	google.golang.org/grpc v1.76.0
	gorm.io/driver/postgres v1.5.4
	gorm.io/driver/sqlite v1.6.0
	gorm.io/gorm v1.30.0
)

require (
	github.com/beorn7/perks v1.0.1 // indirect
	github.com/cespare/xxhash/v2 v2.3.0 // indirect
	github.com/davecgh/go-spew v1.1.1 // indirect
	github.com/jackc/pgpassfile v1.0.0 // indirect
	github.com/jackc/pgservicefile v0.0.0-20221227161230-091c0ba34f0a // indirect
	github.com/jackc/pgx/v5 v5.4.3 // indirect
	github.com/jinzhu/inflection v1.0.0 // indirect
	github.com/jinzhu/now v1.1.5 // indirect
	github.com/mattn/go-sqlite3 v1.14.22 // indirect
	github.com/matttproud/golang_protobuf_extensions/v2 v2.0.0 // indirect
	github.com/pmezard/go-difflib v1.0.0 // indirect
	github.com/prometheus/client_model v0.5.0 // indirect
	github.com/prometheus/common v0.45.0 // indirect
	github.com/prometheus/procfs v0.12.0 // indirect
	go.uber.org/multierr v1.11.0 // indirect
	golang.org/x/crypto v0.40.0 // indirect
	golang.org/x/net v0.42.0 // indirect
	golang.org/x/sys v0.34.0 // indirect
	golang.org/x/text v0.27.0 // indirect
	google.golang.org/genproto/googleapis/rpc v0.0.0-20250804133106-a7a43d27e69b // indirect
	google.golang.org/protobuf v1.36.10 // indirect
	gopkg.in/yaml.v3 v3.0.1 // indirect
)
