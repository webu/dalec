

function dalec_fetch_content(container){
    const data = container.dataset ;
    container.classList.add("dalec-loading");
    fetch(
        data.url,
        {
            method: "POST",
            headers: {
              'Accept': 'text/html',
              'Content-Type': 'application/json'
            },
            // cache: "no-cache",
            body: JSON.stringify(
                {"channelObjects": data.channelObjects, "orderedBy": data.orderedBy}
            ),
            keepalive: true,
        }
    ).then(function(response){
        if (!response.ok) {
            console.error(`HTTP error ${response.status} while fetching ${data.url}`);
            return ;
        }
        if (response.status === 204) {
            container.classList.remove("dalec-loading");
            return ;
        }
        response.text().then(function (html) {
            container.innerHTML = html ;
            container.classList.remove("dalec-loading");
        });
    });
}
