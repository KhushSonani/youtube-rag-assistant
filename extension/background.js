// background.js — Manifest V3 Service Worker
// Minimal: visually indicate on YouTube tabs that the extension is active.

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (
    changeInfo.status === "complete" &&
    tab.url &&
    (tab.url.includes("youtube.com/watch") || tab.url.includes("youtu.be/"))
  ) {
    chrome.action.setBadgeText({ tabId, text: "AI" });
    chrome.action.setBadgeBackgroundColor({ tabId, color: "#6C63FF" });
  } else if (changeInfo.status === "complete") {
    chrome.action.setBadgeText({ tabId, text: "" });
  }
});
