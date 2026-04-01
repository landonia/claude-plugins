---
name: java-guidelines
description: >
  Apply Java coding standards, patterns, and best practices whenever you are writing, reviewing, editing,
  or generating Java code. Trigger this skill when the user asks you to create a Java class, interface,
  enum, or any .java file; when reviewing existing Java code; when the user mentions Java, Spring, Spring Boot,
  Maven, Gradle, JUnit, or any Java framework; or when editing files with a .java extension.
---

# Java Coding Guidelines

Apply these conventions and patterns consistently across all Java code you write or modify.
This project uses **Spring Boot** as the primary framework.

---

## Comments and Javadoc

Good comments explain *why* something is done, not *what* the code literally does — the code already shows what. Write comments as you would explain something to a capable colleague: brief, clear, and human.

### Javadoc — always required on public API

Every public class, interface, enum, and method you create must have a Javadoc comment. Keep it concise — one sentence is often enough. Only add `@param`, `@return`, and `@throws` tags when they add meaning beyond the method signature.

```java
/**
 * Handles order placement and lifecycle management.
 * Delegates persistence to {@link OrderRepository} and payment to {@link PaymentGateway}.
 */
@Service
public class OrderService { ... }

/**
 * Places a new order for the given customer.
 *
 * @param request the order details including items and delivery address
 * @return the persisted order with its assigned ID and initial status
 * @throws OutOfStockException if any requested item is unavailable
 */
public Order placeOrder(PlaceOrderRequest request) { ... }
```

For simple getters, records, and self-explanatory methods a single-line Javadoc is fine:

```java
/** Returns the total price including tax and shipping. */
public BigDecimal getTotal() { ... }
```

### Inline comments — use sparingly, make them count

Add an inline comment only when the logic isn't obvious from the code itself. Prefer a well-named helper method over a comment explaining a long block.

```java
// Retry once on transient network failure — the gateway is eventually consistent
try {
    paymentGateway.charge(order);
} catch (TransientPaymentException e) {
    log.warn("Payment attempt failed, retrying once. orderId={}", order.getId());
    paymentGateway.charge(order);
}
```

Do **not** comment things the code already says clearly:

```java
// BAD — the code is already self-explanatory
int total = items.size(); // get the number of items

// GOOD — no comment needed
int itemCount = items.size();
```

---

## Naming Conventions

- **Classes / Interfaces / Enums / Annotations**: `UpperCamelCase` — `OrderService`, `PaymentGateway`
- **Methods / variables**: `lowerCamelCase` — `calculateTotal()`, `maxRetryCount`
- **Constants**: `UPPER_SNAKE_CASE` — `MAX_CONNECTIONS`, `DEFAULT_TIMEOUT_MS`
- **Packages**: all lowercase, reverse-domain style — `com.example.order.service`
- **Test classes**: suffix with `Test` — `OrderServiceTest`
- **Builder classes**: suffix with `Builder` — `UserBuilder`
- Names must be descriptive. Never use single-letter names except loop indices (`i`, `j`, `k`).

---

## Spring Boot Conventions

### Dependency Injection

Always use **constructor injection**. Spring will inject automatically when there is a single constructor — no `@Autowired` needed. This keeps dependencies explicit and makes classes easy to test without a Spring context.

```java
@Service
public class OrderService {

    private final OrderRepository orderRepository;
    private final PaymentGateway paymentGateway;

    // Spring injects these automatically — no @Autowired needed
    public OrderService(OrderRepository orderRepository, PaymentGateway paymentGateway) {
        this.orderRepository = orderRepository;
        this.paymentGateway = paymentGateway;
    }
}
```

Never use field injection (`@Autowired` on a field) — it hides dependencies and breaks testability.

### Stereotype Annotations

Use the most specific annotation that fits:

| Annotation | Use for |
|---|---|
| `@Service` | Business logic / use-case classes |
| `@Repository` | Data access implementations |
| `@RestController` | HTTP REST endpoints |
| `@Component` | General Spring-managed beans that don't fit the above |
| `@Configuration` | Spring configuration classes that declare `@Bean` methods |

### REST Controllers

Keep controllers thin — they translate HTTP to method calls and back, nothing more. All logic lives in the service.

```java
/**
 * REST endpoints for order management.
 * All business logic is delegated to {@link OrderService}.
 */
@RestController
@RequestMapping("/api/v1/orders")
public class OrderController {

    private final OrderService orderService;

    public OrderController(OrderService orderService) {
        this.orderService = orderService;
    }

    /**
     * Places a new order.
     *
     * @param request the order details from the request body
     * @return the created order with HTTP 201
     */
    @PostMapping
    public ResponseEntity<OrderResponse> placeOrder(@RequestBody @Valid PlaceOrderRequest request) {
        var order = orderService.placeOrder(request);
        return ResponseEntity.status(HttpStatus.CREATED).body(OrderResponse.from(order));
    }

    /**
     * Retrieves an order by ID.
     *
     * @param id the order ID from the URL path
     * @return the order if found, or 404
     */
    @GetMapping("/{id}")
    public ResponseEntity<OrderResponse> getOrder(@PathVariable UUID id) {
        var order = orderService.getOrder(id);
        return ResponseEntity.ok(OrderResponse.from(order));
    }
}
```

### Configuration Properties

Bind configuration to a typed class rather than injecting `@Value` fields individually. This groups related config, validates on startup, and is self-documenting.

```java
/**
 * Configuration properties for the payment gateway integration.
 * Values are read from application.yml under the 'payment' prefix.
 */
@ConfigurationProperties(prefix = "payment")
public record PaymentProperties(String apiUrl, Duration timeout, int maxRetries) {}
```

```yaml
# application.yml
payment:
  api-url: https://payments.example.com
  timeout: 5s
  max-retries: 3
```

Enable with `@EnableConfigurationProperties(PaymentProperties.class)` on your `@Configuration` class.

### Exception Handling

Use a `@RestControllerAdvice` class to handle exceptions centrally. Controllers should not contain `try/catch` blocks.

```java
/**
 * Translates domain exceptions into consistent HTTP error responses.
 * Keeps exception-handling logic out of individual controllers.
 */
@RestControllerAdvice
public class GlobalExceptionHandler {

    private static final Logger log = LoggerFactory.getLogger(GlobalExceptionHandler.class);

    /**
     * Handles requests for resources that don't exist.
     */
    @ExceptionHandler(OrderNotFoundException.class)
    public ResponseEntity<ErrorResponse> handleNotFound(OrderNotFoundException ex) {
        log.warn("Resource not found: {}", ex.getMessage());
        return ResponseEntity.status(HttpStatus.NOT_FOUND)
            .body(new ErrorResponse(ex.getMessage()));
    }

    /**
     * Catches unexpected errors so the API always returns a structured response.
     */
    @ExceptionHandler(Exception.class)
    public ResponseEntity<ErrorResponse> handleUnexpected(Exception ex) {
        log.error("Unexpected error", ex);
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
            .body(new ErrorResponse("An unexpected error occurred"));
    }
}
```

### Spring Data JPA Repositories

Extend `JpaRepository` — you get standard CRUD for free. Only add methods for queries the service actually needs.

```java
/**
 * Persistence operations for {@link Order}.
 * Spring Data generates implementations automatically at runtime.
 */
@Repository
public interface OrderRepository extends JpaRepository<Order, UUID> {

    /** Returns all orders placed by the given customer, newest first. */
    List<Order> findByCustomerIdOrderByCreatedAtDesc(UUID customerId);

    /** Returns orders in the given status, for use in background processing jobs. */
    List<Order> findByStatus(OrderStatus status);
}
```

---

## Class Design

- Follow the **Single Responsibility Principle**: one class, one reason to change.
- Prefer **composition over inheritance**. Use inheritance only for genuine "is-a" relationships.
- Keep classes **small and focused** — if a class exceeds ~300 lines, consider splitting it.
- Make fields `private` by default. Expose only what is needed via well-named methods.
- Mark classes and methods `final` unless you intend them to be extended.
- Avoid public mutable state. Prefer immutable objects where possible.

---

## Common Design Patterns

### Builder Pattern

Use for objects with many optional fields. In Spring Boot projects, prefer Lombok's `@Builder` to reduce boilerplate, but write it by hand if Lombok is not available.

```java
/**
 * Represents a customer notification to be sent via email or SMS.
 * Use {@link Builder} to construct instances — direct construction is not allowed.
 */
public final class Notification {

    private final UUID recipientId;
    private final String subject;
    private final String body;
    private final NotificationType type;

    private Notification(Builder builder) {
        this.recipientId = builder.recipientId;
        this.subject = builder.subject;
        this.body = builder.body;
        this.type = builder.type;
    }

    /** Builder for {@link Notification}. {@code recipientId} and {@code type} are required. */
    public static final class Builder {
        private final UUID recipientId;
        private final NotificationType type;
        private String subject;
        private String body;

        public Builder(UUID recipientId, NotificationType type) {
            this.recipientId = recipientId;
            this.type = type;
        }

        public Builder subject(String subject) { this.subject = subject; return this; }
        public Builder body(String body) { this.body = body; return this; }

        /** Constructs the {@link Notification}. */
        public Notification build() { return new Notification(this); }
    }
}
```

### Factory Method Pattern

Use when creation logic is complex or the concrete type may vary at runtime.

```java
/**
 * Creates {@link PaymentProcessor} instances for a given payment method.
 * Add a new case here when a new payment method is supported — no other class needs to change.
 */
@Component
public class PaymentProcessorFactory {

    private final StripeProcessor stripeProcessor;
    private final PayPalProcessor payPalProcessor;

    public PaymentProcessorFactory(StripeProcessor stripeProcessor, PayPalProcessor payPalProcessor) {
        this.stripeProcessor = stripeProcessor;
        this.payPalProcessor = payPalProcessor;
    }

    /**
     * Returns the processor for the given payment method.
     *
     * @throws IllegalArgumentException if the payment method is not supported
     */
    public PaymentProcessor forMethod(PaymentMethod method) {
        return switch (method) {
            case STRIPE -> stripeProcessor;
            case PAYPAL -> payPalProcessor;
        };
    }
}
```

### Strategy Pattern

Encapsulate interchangeable algorithms behind a common interface. In Spring, you can inject all implementations as a list and select at runtime.

```java
/**
 * Calculates the final price for an order given a base price.
 * Implementations represent different pricing rules (e.g. seasonal discount, loyalty reward).
 */
@FunctionalInterface
public interface PricingStrategy {
    /** @return the adjusted price — never negative */
    BigDecimal calculate(BigDecimal basePrice);
}
```

### Service Layer Pattern

Keep business logic in the service. The controller maps HTTP; the service owns the rules; the repository owns the data.

```java
/**
 * Manages the full lifecycle of an order from placement through to fulfilment.
 */
@Service
public class OrderService {

    private static final Logger log = LoggerFactory.getLogger(OrderService.class);

    private final OrderRepository orderRepository;
    private final InventoryService inventoryService;
    private final PaymentGateway paymentGateway;

    public OrderService(
            OrderRepository orderRepository,
            InventoryService inventoryService,
            PaymentGateway paymentGateway) {
        this.orderRepository = orderRepository;
        this.inventoryService = inventoryService;
        this.paymentGateway = paymentGateway;
    }

    /**
     * Places a new order, reserving inventory and charging the customer.
     *
     * @param request the validated order request
     * @return the saved order with its assigned ID
     * @throws OutOfStockException if any item in the order is unavailable
     */
    public Order placeOrder(PlaceOrderRequest request) {
        inventoryService.reserveItems(request.items()); // throws if any item is out of stock

        var order = Order.builder()
            .customerId(request.customerId())
            .items(request.items())
            .status(OrderStatus.PENDING)
            .build();

        var saved = orderRepository.save(order);
        log.info("Order placed. orderId={} customerId={}", saved.getId(), saved.getCustomerId());

        paymentGateway.charge(saved);
        return saved;
    }
}
```

---

## Package Structure

Organise by feature (vertical slices), not by layer. Each feature package is self-contained.

```
com.example.app
├── order/
│   ├── Order.java              # JPA entity / domain model
│   ├── OrderService.java       # business logic
│   ├── OrderRepository.java    # Spring Data interface
│   ├── OrderController.java    # REST endpoints
│   ├── OrderStatus.java        # enum for order state
│   └── dto/
│       ├── PlaceOrderRequest.java
│       └── OrderResponse.java
├── payment/
│   ├── PaymentGateway.java     # interface — keeps the service decoupled from providers
│   ├── StripeProcessor.java
│   └── PaymentProcessorFactory.java
└── shared/
    ├── exception/              # GlobalExceptionHandler and custom exceptions
    └── config/                 # Spring @Configuration classes
```

Avoid flat `service/`, `controller/`, `repository/` top-level packages — they make features hard to reason about as a unit.

---

## DTOs and Records

Use Java **records** for request/response DTOs — they are immutable and require no boilerplate.

```java
/**
 * Request body for placing a new order.
 * Validated on arrival at the controller via {@code @Valid}.
 */
public record PlaceOrderRequest(
    @NotNull UUID customerId,
    @NotEmpty List<@Valid OrderItem> items,
    @NotNull DeliveryAddress deliveryAddress
) {}

/**
 * API response for a single order. Constructed from an {@link Order} entity.
 */
public record OrderResponse(UUID id, OrderStatus status, BigDecimal total) {

    /** Converts an {@link Order} entity into an API response. */
    public static OrderResponse from(Order order) {
        return new OrderResponse(order.getId(), order.getStatus(), order.getTotal());
    }
}
```

---

## Exception Handling

- Create a specific exception class for each distinct domain error.
- Use unchecked exceptions (`RuntimeException` subclasses) for domain errors that the caller cannot recover from locally.
- Let `GlobalExceptionHandler` decide the HTTP status — never set it in the service.

```java
/**
 * Thrown when an order cannot be found by the given ID.
 * Mapped to HTTP 404 by {@link GlobalExceptionHandler}.
 */
public class OrderNotFoundException extends RuntimeException {

    public OrderNotFoundException(UUID orderId) {
        super("Order not found: " + orderId);
    }
}
```

- Never swallow exceptions silently (`catch (Exception e) {}`).
- Only catch what you can meaningfully handle at that level — let everything else propagate.
- Use `try-with-resources` for all `Closeable` / `AutoCloseable` resources.

---

## Validation

Use Bean Validation (`jakarta.validation`) on DTOs and let Spring wire it up automatically.

```java
public record PlaceOrderRequest(
    @NotNull(message = "Customer ID is required") UUID customerId,
    @NotEmpty(message = "Order must contain at least one item") List<OrderItem> items
) {}
```

Activate in the controller with `@Valid` on the request body parameter. Spring will return 400 automatically for constraint violations — you do not need to write that code yourself.

---

## Optionals

- Use `Optional<T>` as a return type when a value may be absent — never as a method parameter or field type.
- Never call `.get()` without first checking — prefer `.orElseThrow()`, `.orElse()`, or `.ifPresent()`.

```java
orderRepository.findById(id)
    .orElseThrow(() -> new OrderNotFoundException(id));
```

---

## Streams and Collections

- Prefer streams for transformations and filtering over manual loops.
- Keep stream pipelines readable — break long chains across lines.
- Return the most general useful type: `List` over `ArrayList`, `Map` over `HashMap`.
- Never return `null` for collections — return an empty collection instead.

---

## Testing

- One test class per production class, named `<ClassName>Test`.
- Use **JUnit 5** (`@Test`, `@BeforeEach`, `@DisplayName`).
- Use **Mockito** to mock collaborators; verify behaviour, not internal implementation details.
- Follow **Arrange / Act / Assert** with blank lines separating each phase.
- Test method names describe the scenario: `placeOrder_whenItemOutOfStock_throwsException`.
- For Spring Boot integration tests use `@SpringBootTest` + `@AutoConfigureMockMvc`.
- For unit tests there is no need to load a Spring context — just `new` the class under test with mocked dependencies.

```java
class OrderServiceTest {

    // Mocked so tests run without a database or real payment provider
    @Mock private OrderRepository orderRepository;
    @Mock private PaymentGateway paymentGateway;

    private OrderService orderService;

    @BeforeEach
    void setUp() {
        MockitoAnnotations.openMocks(this);
        orderService = new OrderService(orderRepository, paymentGateway);
    }

    @Test
    @DisplayName("placeOrder throws when an item is out of stock")
    void placeOrder_whenItemOutOfStock_throwsException() {
        // Arrange
        var request = new PlaceOrderRequest(CUSTOMER_ID, List.of(OUT_OF_STOCK_ITEM), ADDRESS);
        when(inventoryService.isAvailable(OUT_OF_STOCK_ITEM)).thenReturn(false);

        // Act & Assert
        assertThrows(OutOfStockException.class, () -> orderService.placeOrder(request));
    }
}
```

---

## Code Style

- Use the **Google Java Style Guide** as a baseline.
- Indent with **4 spaces** (not tabs).
- Line length: **120 characters** max.
- Always include braces `{}` even for single-line `if`/`for`/`while` bodies.
- Add a blank line between methods.
- Annotate overridden methods with `@Override`.
- Use `var` for local variables when the type is obvious from the right-hand side:
  ```java
  var order = orderRepository.findById(id).orElseThrow(...);
  ```

---

## Logging

- Use **SLF4J** with the Spring Boot default backend (Logback). Never use `System.out.println`.
- Declare the logger as `private static final`:
  ```java
  private static final Logger log = LoggerFactory.getLogger(OrderService.class);
  ```
- Use parameterised messages — never string concatenation:
  ```java
  log.info("Order placed. orderId={} customerId={}", order.getId(), order.getCustomerId());
  ```
- Log at the right level: `DEBUG` for diagnostic detail, `INFO` for key lifecycle events, `WARN` for recoverable issues, `ERROR` for failures that need attention.

---

## What to Avoid

- `null` returns from public methods — use `Optional` or empty collections.
- Static mutable state.
- Catching `Throwable` or `Error`.
- God classes or utility classes with dozens of unrelated static methods.
- Abbreviations in names (`usrSvc`, `ord`) — spell things out.
- Checked exceptions for unrecoverable domain errors — use unchecked runtime exceptions.
- `@Autowired` field injection — use constructor injection instead.
- Business logic in controllers — keep them thin.
- Hardcoded configuration values — use `@ConfigurationProperties` and `application.yml`.
