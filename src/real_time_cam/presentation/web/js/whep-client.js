// @ts-check
/**
 * Minimal, standards-compliant WebRTC-HTTP Egress Protocol (WHEP) player client.
 * Handles SDP offer/answer negotiation, offline-LAN ICE gathering, and cleanup.
 */

import {
  HTTP_STATUS_FORBIDDEN,
  HTTP_STATUS_NOT_FOUND,
  HTTP_STATUS_UNAUTHORIZED,
  ICE_GATHER_TIMEOUT_MS,
  PlayerState,
} from "./constants.js";

/**
 * @typedef {Object} WhepClientCallbacks
 * @property {(state: string, messageFa: string) => void} onStateChange
 * @property {(stream: MediaStream) => void} onMediaStream
 */

export class WhepHandshakeError extends Error {
  /**
   * @param {string} messageFa - User-facing Persian explanation.
   * @param {number | null} [httpStatus=null] - HTTP status code if available.
   */
  constructor(messageFa, httpStatus = null) {
    super(messageFa);
    this.name = "WhepHandshakeError";
    this.httpStatus = httpStatus;
  }
}

/**
 * Wait until local ICE host candidates are gathered (fast on offline LAN).
 *
 * @param {RTCPeerConnection} peerConnection
 * @param {number} timeoutMs
 * @returns {Promise<void>}
 */
export function waitForIceGatheringComplete(
  peerConnection,
  timeoutMs = ICE_GATHER_TIMEOUT_MS,
) {
  if (peerConnection.iceGatheringState === "complete") {
    return Promise.resolve();
  }
  return new Promise((resolve) => {
    const timerId = globalThis.setTimeout(() => {
      peerConnection.removeEventListener("icegatheringstatechange", checkState);
      resolve();
    }, timeoutMs);

    function checkState() {
      if (peerConnection.iceGatheringState !== "complete") {
        return;
      }
      globalThis.clearTimeout(timerId);
      peerConnection.removeEventListener("icegatheringstatechange", checkState);
      resolve();
    }

    peerConnection.addEventListener("icegatheringstatechange", checkState);
  });
}

/**
 * Map HTTP WHEP status codes to clear Persian operator messages.
 *
 * @param {number} status
 * @returns {string}
 */
export function describeHttpFailureFa(status) {
  if (status === HTTP_STATUS_NOT_FOUND) {
    return "سرور MediaMTX روشن است، اما هنوز تصویری روی مسیر cam ارسال نمی‌شود (اسکریپت رزبری‌پای را بررسی کنید).";
  }
  if (status === HTTP_STATUS_UNAUTHORIZED || status === HTTP_STATUS_FORBIDDEN) {
    return "دسترسی به جریان ویدیو مجاز نیست (خطای احراز هویت).";
  }
  return `پاسخ غیرمنتظره از سرور MediaMTX (کد HTTP ${status}).`;
}

/**
 * Resolve optional relative `Location` header into an absolute WHEP session URL.
 *
 * @param {string} whepEndpointUrl
 * @param {string | null} locationHeader
 * @returns {string | null}
 */
function resolveSessionUrl(whepEndpointUrl, locationHeader) {
  if (!locationHeader) {
    return null;
  }
  try {
    return new URL(locationHeader, whepEndpointUrl).toString();
  } catch {
    return null;
  }
}

export class WhepPlayerClient {
  /**
   * @param {WhepClientCallbacks} callbacks
   */
  constructor(callbacks) {
    /** @private */
    this._callbacks = callbacks;
    /** @private @type {RTCPeerConnection | null} */
    this._peerConnection = null;
    /** @private @type {string | null} */
    this._sessionResourceUrl = null;
  }

  /**
   * Negotiate a new WHEP receive-only video session with MediaMTX.
   *
   * @param {string} whepEndpointUrl
   * @returns {Promise<void>}
   */
  async connect(whepEndpointUrl) {
    await this.disconnect(false);
    this._callbacks.onStateChange(
      PlayerState.CONNECTING,
      "در حال مذاکره WebRTC (WHEP) با سرور رسانه...",
    );

    const peerConnection = new RTCPeerConnection({ iceServers: [] });
    this._peerConnection = peerConnection;
    this._bindPeerEvents(peerConnection);
    peerConnection.addTransceiver("video", { direction: "recvonly" });

    try {
      const answerSdp = await this._exchangeSdpWithWhep(
        peerConnection,
        whepEndpointUrl,
      );
      await peerConnection.setRemoteDescription({
        type: "answer",
        sdp: answerSdp,
      });
    } catch (err) {
      await this.disconnect(false);
      const messageFa =
        err instanceof WhepHandshakeError
          ? err.message
          : "امکان برقراری ارتباط با سرور MediaMTX وجود ندارد؛ روشن بودن سرور و آدرس WHEP را بررسی کنید.";
      this._callbacks.onStateChange(PlayerState.ERROR, messageFa);
    }
  }

  /**
   * Close active RTCPeerConnection and release server WHEP session if known.
   *
   * @param {boolean} [shouldEmitIdle=true]
   * @returns {Promise<void>}
   */
  async disconnect(shouldEmitIdle = true) {
    const sessionUrl = this._sessionResourceUrl;
    this._sessionResourceUrl = null;

    if (this._peerConnection !== null) {
      this._peerConnection.close();
      this._peerConnection = null;
    }
    if (sessionUrl !== null) {
      try {
        await globalThis.fetch(sessionUrl, { method: "DELETE" });
      } catch {
        // Ignore network errors while tearing down an old session.
      }
    }
    if (shouldEmitIdle) {
      this._callbacks.onStateChange(PlayerState.IDLE, "پخش متوقف شد.");
    }
  }

  /**
   * @private
   * @param {RTCPeerConnection} peerConnection
   * @param {string} whepEndpointUrl
   * @returns {Promise<string>}
   */
  async _exchangeSdpWithWhep(peerConnection, whepEndpointUrl) {
    const offer = await peerConnection.createOffer();
    await peerConnection.setLocalDescription(offer);
    await waitForIceGatheringComplete(peerConnection);

    const localDesc = peerConnection.localDescription;
    if (!localDesc || !localDesc.sdp) {
      throw new WhepHandshakeError("تولید پیشنهاد SDP در مرورگر ناموفق بود.");
    }

    const response = await globalThis.fetch(whepEndpointUrl, {
      method: "POST",
      headers: { "Content-Type": "application/sdp" },
      body: localDesc.sdp,
    });
    if (!response.ok) {
      throw new WhepHandshakeError(
        describeHttpFailureFa(response.status),
        response.status,
      );
    }
    this._sessionResourceUrl = resolveSessionUrl(
      whepEndpointUrl,
      response.headers.get("Location"),
    );
    return response.text();
  }

  /**
   * @private
   * @param {RTCPeerConnection} peerConnection
   */
  _bindPeerEvents(peerConnection) {
    peerConnection.addEventListener("track", (event) => {
      const mediaStream =
        event.streams && event.streams[0]
          ? event.streams[0]
          : new MediaStream([event.track]);
      this._callbacks.onMediaStream(mediaStream);
    });

    peerConnection.addEventListener("connectionstatechange", () => {
      if (this._peerConnection !== peerConnection) {
        return;
      }
      const connState = peerConnection.connectionState;
      if (connState === "connected") {
        this._callbacks.onStateChange(
          PlayerState.LIVE,
          "ارتباط مستقیم WebRTC برقرار شد.",
        );
        return;
      }
      if (connState === "failed" || connState === "disconnected") {
        this._callbacks.onStateChange(
          PlayerState.ERROR,
          "ارتباط زنده تصویر قطع شد؛ وضعیت شبکه یا ارسال رزبری‌پای را بررسی کنید.",
        );
      }
    });
  }
}
