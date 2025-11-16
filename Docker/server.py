from fastapi import FastAPI, WebSocket
import asyncio, json, time, logging
import receiver

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("cubesat")

app = FastAPI()

# Onboard state
state = {"mode": "IDLE"}

# Simulated processing latency for uplink commands (seconds)
COMMAND_LATENCY_S = 2.0

@app.get("/health")
def health():
    return {"ok": True, "state": state}

@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    log.info("Ground connected")

    cmd_queue: asyncio.Queue = asyncio.Queue()
    running = True

    async def recv_loop():
        """Receive uplink commands and enqueue them for delayed processing."""
        while running:
            text = await ws.receive_text()
            try:
                msg = json.loads(text)
            except json.JSONDecodeError:
                continue
            # attach a sequence id if none provided
            seq = msg.get("seq") or int(time.time() * 1000)
            await cmd_queue.put({"cmd": msg, "seq": seq, "recv_ts": time.time()})

    async def process_loop():
        """Process queued commands with artificial latency, then send ACK."""
        while running:
            item = await cmd_queue.get()
            cmd = item["cmd"]
            seq = item["seq"]
            await asyncio.sleep(COMMAND_LATENCY_S)  # simulate comm/processing delay

            # Apply command to onboard state
            c = cmd.get("command")
            if c == "set_mode":
                mode = cmd.get("mode")
                if mode in {"IDLE", "SAFE", "SCIENCE"}:
                    state["mode"] = mode
                    try:
                        if mode == "SAFE":
                            receiver.send_uplink_command("SAFE")
                        elif mode == "SCIENCE":
                            receiver.send_uplink_command("SCIENCE")
                        elif mode == "IDLE":
                            receiver.send_uplink_command("IDLE")
                    except Exception as e:
                        log.error(f"Failed to send uplink: {e}")

            # Send ACK after processing
            ack = {
                "type": "ack",
                "status": "OK",
                "seq": seq,
                "command": c,
                "applied_state": state,
                "applied_at": time.time(),
            }
            await ws.send_json(ack)

    async def telemetry_loop():
        while running:
            telem = receiver.read_sensor_data()
            payload = {
                "type": "telemetry",
                "source": "rfm69_downlink",
                "queue_depth": cmd_queue.qsize(),
                **telem,
                **state,
            }
            await ws.send_json(payload)
            await asyncio.sleep(1.0)

    tasks = [
        asyncio.create_task(recv_loop()),
        asyncio.create_task(process_loop()),
        asyncio.create_task(telemetry_loop()),
    ]

    try:
        await asyncio.gather(*tasks)
    except Exception as e:
        log.exception("Server error: %s", e)
    finally:
        for t in tasks:
            t.cancel()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)