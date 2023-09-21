function dalec_fetch_content(container) {
  const [orderedBy, url] = [container.dataset.orderedBy, container.dataset.url];
  let channelObjects = container.dataset.channelObjects;

  container.classList.add("dalec-loading");
  container.classList.remove("dalec-loading-error");
  if (channelObjects !== undefined) {
    channelObjects = JSON.parse(channelObjects);
  }
  fetch(url, {
    method: "POST",
    headers: {
      Accept: "text/html",
      "Content-Type": "application/json",
    },
    // cache: "no-cache",
    body: JSON.stringify({
      channelObjects: channelObjects,
      orderedBy: orderedBy,
    }),
    keepalive: true,
  }).then(function (response) {
    if (!response.ok) {
      container.classList.remove("dalec-loading");
      container.classList.add("dalec-loading-error");
      console.error(`HTTP error ${response.status} while fetching ${url}`);
      return;
    }
    if (response.status === 204) {
      container.classList.remove("dalec-loading");
      return;
    }
    response.text().then(function (html) {
      container.innerHTML = html;
      container.classList.remove("dalec-loading");
    });
  });
}

module.exports = dalec_fetch_content;
