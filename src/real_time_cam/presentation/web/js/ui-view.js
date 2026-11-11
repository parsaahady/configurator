// @ts-check
/**
 * DOM view adapter for the Step 3 Ground-Control video viewport.
 * Keeps all HTML element mutations isolated from WebRTC protocol logic.
 */

import { PlayerState, STATE_LABELS_FA } from "./constants.js";

/**
 * @typedef {Object} PlayerDomElements
 * @property {HTMLVideoElement} videoEl
 * @property {HTMLElement} videoStageEl
 * @property {HTMLElement} stateBadgeEl
 * @property {HTMLElement} resolutionPillEl
 * @property {HTMLElement} statusBannerEl
 * @property {HTMLInputElement} whepUrlInputEl
 * @property {HTMLButtonElement} connectBtnEl
 * @property {HTMLButtonElement} disconnectBtnEl
 * @property {HTMLButtonElement} fullscreenBtnEl
 */

export class PlayerUiView {
  /**
   * @param {PlayerDomElements} elements
   */
  constructor(elements) {
    /** @private */
    this._el = elements;
  }

  /**
   * Update state badge, status banner, and control button availability.
   *
   * @param {string} state
   * @param {string} messageFa
   */
  renderState(state, messageFa) {
    const labelFa = STATE_LABELS_FA[state] ?? STATE_LABELS_FA[PlayerState.IDLE];
    this._el.stateBadgeEl.textContent = labelFa;
    this._el.stateBadgeEl.dataset.state = state;

    this._el.statusBannerEl.textContent = messageFa;
    this._el.statusBannerEl.dataset.state = state;

    const isConnecting = state === PlayerState.CONNECTING;
    const isActive = isConnecting || state === PlayerState.LIVE;
    this._el.connectBtnEl.disabled = isConnecting;
    this._el.disconnectBtnEl.disabled = !isActive;

    if (state !== PlayerState.LIVE) {
      this._el.resolutionPillEl.textContent = "—";
    }
  }

  /**
   * Attach incoming MediaStream to `<video>` and start low-latency playback.
   *
   * @param {MediaStream} mediaStream
   */
  attachStream(mediaStream) {
    const videoEl = this._el.videoEl;
    videoEl.srcObject = mediaStream;
    videoEl.muted = true;
    videoEl.playsInline = true;
    videoEl.play().catch(() => {
      this.renderState(
        PlayerState.ERROR,
        "مرورگر پخش خودکار ویدیو را مسدود کرد؛ روی دکمه اتصال کلیک کنید.",
      );
    });
  }

  /**
   * Detach current stream from `<video>` when disconnecting.
   */
  clearVideo() {
    this._el.videoEl.srcObject = null;
    this._el.resolutionPillEl.textContent = "—";
  }

  /**
   * Display decoded frame dimensions (`WIDTH×HEIGHT px`) once metadata arrives.
   */
  refreshDecodedResolution() {
    const widthPx = this._el.videoEl.videoWidth;
    const heightPx = this._el.videoEl.videoHeight;
    if (widthPx > 0 && heightPx > 0) {
      this._el.resolutionPillEl.textContent = `${widthPx}×${heightPx} px`;
    }
  }

  /**
   * Toggle browser fullscreen mode on the video stage container.
   *
   * @returns {Promise<void>}
   */
  async toggleFullscreen() {
    if (document.fullscreenElement) {
      await document.exitFullscreen();
      return;
    }
    await this._el.videoStageEl.requestFullscreen();
  }
}
