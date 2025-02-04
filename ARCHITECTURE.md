# Architecture

The agent is built on an event-driven architecture with three main components:

### 1. Listeners
- **Telegram Listener**: Handles admin commands through a Telegram bot interface
- **OnChain Listener**: Monitors blockchain events and user messages
  - Tracks Morpho Protocol events
  - Processes user messages through on-chain transactions

### 2. Event Processing Graphs
The agent uses LangGraph to process different types of events through specialized graphs:

#### AdminGraph
- **Purpose**: Process admin commands and control agent behavior
- **Flow**:
  - Interpret command intent (research/action)
  - Route to appropriate processor
  - Execute commands or provide analysis
- **Models**: Uses Claude 3 Haiku for interpretation, Sonnet for execution

#### UserMessageGraph (Planned)
- **Purpose**: Handle user interactions through on-chain messages
- **Capabilities**:
  - Process user requests
  - Execute permitted vault operations
  - Provide position information

#### AnalyzeGraph (Planned)
- **Purpose**: Market analysis and strategy optimization
- **Capabilities**:
  - Monitor market conditions
  - Analyze vault performance
  - Recommend (Execute) reallocation strategies

