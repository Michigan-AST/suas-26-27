# suas-26-27

Code and documentation for the M-AST 2026-27 drone for the S.U.A.S competition.

## Prerequisites

- **Docker Desktop** (macOS/Linux/Windows)
- **QGroundControl** (installed on host)
- **Python 3.9+** and `make`

## Quick Start

### 1. Configure Docker Networking (macOS)

In Docker Desktop, navigate to **Settings > Resources > Network** and enable **Enable host networking**. Apply and restart Docker Desktop.

Make sure Docker Desktop is running, if you're using it.

### 2. Launch QGroundControl

Open the **QGroundControl** application on your computer. Just leave it running in the background. It listens on UDP port `14550`.

### 3. Start the SITL Simulation

From the repository root, start PX4 and the Gazebo simulation:

```bash
bash sitl.sh
```

To speed up the simulation (e.g. 2x real-time speed):

```bash
bash sitl.sh --speed 2
# or: PX4_SIM_SPEED_FACTOR=2 bash sitl.sh
```

This builds the `suas-px4-sitl:v1.17.0` image (if not already built) and launches PX4 with the fixed-wing RC Cessna model (`gz_rc_cessna`) in headless mode.

### 4. Run the Python Flight Script

In a _new_ terminal window from the repository root:

```bash
# Setup virtual environment and install dependencies (first time or on dependency change)
make venv

# Run flight instructions
make run
```

The script connects to PX4 over UDP `14540` and executes the autonomous mission defined in `scripts/drone_control.py`.

### 5. Stop the Simulation

To shut down the simulation container:

```bash
docker stop suas-px4-sitl
```

---

## Python Development & Testing

- **Edit Flight Instructions**: Modify `flight_instructions()` at the top of [`scripts/drone_control.py`](scripts/drone_control.py).

- **Run Tests**:
  ```bash
  make test
  ```
- **Custom Python Interpreter**:
  ```bash
  make venv PYTHON=python3.11
  ```

---

## Troubleshooting

### QGroundControl Connection

If QGroundControl does not connect automatically:

1. Open **Application Settings > Comm Links**.
2. Disable UDP auto-connect.
3. Add a manual UDP link with listening port `14550` and target host `127.0.0.1:18570`.

### Docker Image Export Failures

If you see `failed to receive status ... error reading from server: EOF` during layer export:

1. Confirm Docker Desktop is running and has sufficient disk space/memory allocated.
2. Rebuild directly with detailed output:
   ```bash
   docker build --progress=plain -f docker/sitl.dockerfile -t suas-px4-sitl:v1.17.0 .
   ```
3. Inspect the image configuration:
   ```bash
   docker image inspect suas-px4-sitl:v1.17.0 --format 'Workdir={{.Config.WorkingDir}} Command={{json .Config.Cmd}}'
   ```
