

function dalec_fetch_content(container){
    const data = container.dataset ;
    fetch(
        data.url,
        {
            method: "GET",
            // cache: "no-cache",
            keepalive: true,
        }
    ).then(function(response){
        if (!response.ok) {
            console.error(`HTTP error ${reponse.status} while fetching ${data.url}`);
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
