

function dalec_fetch_content(container){
    const data = container.dataset ;
    fetch(
        data.url,
        {
            method: "POST",
            headers: {
              'Accept': 'text/html',
              'Content-Type': 'application/json'
            },
            // cache: "no-cache",
            body: data.channelObjects,
            keepalive: true,
        }
    ).then(function(response){
        if (!response.ok) {
            console.error(`HTTP error ${response.status} while fetching ${data.url}`);
            return ;
        }
        if (response.status === 204) {
            return ;
        }
        response.text().then(function (html) {
            container.innerHTML = html ;
        });
    });
}
