// @ts-check
/**
 * Browser entrypoint wiring PlayerUiView and WhepPlayerClient.
 */

import { buildDefaultWhepUrl, PlayerState } from "./constants.js";
import { PlayerUiView } from "./ui-view.js";
import { WhepPlayerClient } from "./whep-client.js";

/**
 * Look up a required DOM element by ID or throw a descriptive error.
 *
 * @template {HTMLElement} T
 * @param {string} id
 * @returns {T}
 */
function requireElement(id) {
  const element = /** @type {T | null} */ (document.getElementById(id));
  if (!element) {
    throw new Error(`Missing required DOM element: #${id}`);
  }
  return element;
}

function bootstrapPlayerApp() {
  /** @type {import("./ui-view.js").PlayerDomElements} */
  const elements = {
    videoEl: requireElement("live-video"),
    videoStageEl: requireElement("video-stage"),
    stateBadgeEl: requireElement("connection-badge"),
    resolutionPillEl: requireElement("resolution-pill"),
    statusBannerEl: requireElement("status-banner"),
    whepUrlInputEl: requireElement("whep-url-input"),
    connectBtnEl: requireElement("connect-btn"),
    disconnectBtnEl: requireElement("disconnect-btn"),
    fullscreenBtnEl: requireElement("fullscreen-btn"),
  };

  const view = new PlayerUiView(elements);
  const whepClient = new WhepPlayerClient({
    onStateChange: (state, messageFa) => view.renderState(state, messageFa),
    onMediaStream: (stream) => view.attachStream(stream),
  });

  elements.whepUrlInputEl.value = buildDefaultWhepUrl(window.location);
  view.renderState(PlayerState.IDLE, "آماده برقراری ارتباط با دوربین کوادکوپتر.");

  elements.videoEl.addEventListener("loadedmetadata", () => {
    view.refreshDecodedResolution();
  });
  elements.videoEl.addEventListener("resize", () => {
    view.refreshDecodedResolution();
  });

  elements.connectBtnEl.addEventListener("click", () => {
    const targetUrl = elements.whepUrlInputEl.value.trim();
    if (!targetUrl) {
      view.renderState(PlayerState.ERROR, "لطفاً آدرس WHEP سرور را وارد کنید.");
      return;
    }
    void whepClient.connect(targetUrl);
  });

  elements.disconnectBtnEl.addEventListener("click", () => {
    view.clearVideo();
    void whepClient.disconnect(true);
  });

  elements.fullscreenBtnEl.addEventListener("click", () => {
    void view.toggleFullscreen();
  });

  window.addEventListener("beforeunload", () => {
    void whepClient.disconnect(false);
  });

  void whepClient.connect(elements.whepUrlInputEl.value);
}

bootstrapPlayerApp();
