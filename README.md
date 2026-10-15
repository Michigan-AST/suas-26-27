# suas-26-27

Code and documentation for the M-AST 2026-27 drone for the S.U.A.S competition

## PX4 and Gazebo with Docker

On macOS, start Docker Desktop and enable **Settings > Resources > Network > Enable host networking**. Install QGroundControl on the Mac; it runs outside the container.

From the repository root:

```bash
bash build_and_run.sh
```

The script builds the `suas` image, opens QGroundControl, and starts PX4 with the X500 Gazebo model in headless mode. It exits if a command fails. In particular, a failed build cannot continue by launching an older image under the same tag.

QGroundControl listens on UDP port `14550`. If a manual connection is needed, disable UDP auto-connect and configure a UDP Comm Link with listening port `14550` and remote host `127.0.0.1:18570` for PX4 instance zero.

Stop the simulation from another Mac terminal:

```bash
docker stop suas-sitl
```

### Image export failures

An error such as `failed to receive status ... error reading from server: EOF` while exporting layers indicates that the build client's connection to Docker ended. It does not establish why the connection ended, and the `suas` tag may still refer to an older image. Confirm Docker Desktop is running and retry with detailed output while keeping the build cache:

```bash
docker build --progress=plain -f docker/Dockerfile -t suas .
```

After a successful build, the image's working directory should be `/PX4-Autopilot`, and its default command should be `make px4_sitl gz_x500`:

```bash
docker image inspect suas --format 'Workdir={{.Config.WorkingDir}} Command={{json .Config.Cmd}}'
```
