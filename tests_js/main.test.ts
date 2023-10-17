import { fetch_content } from "../dalec/static/dalec/js/main.js";

let dalecContainer: HTMLElement;

describe("fetch_content", () => {
  describe("without channelObjects nor orderBy", () => {
    beforeAll(() => {
      document.body.innerHTML = `
                <div id="dalec-1" data-url="http://test.url"></div>
            `;
      global.fetch = jest.fn(() => {
        expect(dalecContainer.classList).toContain("dalec-loading");
        return Promise.resolve({
          ok: true,
          text: () => Promise.resolve("<div>response</div>"),
        });
      }) as jest.Mock;
      dalecContainer = document.getElementById("dalec-1");
      fetch_content(dalecContainer);
    });

    it("should fetch url", () => {
      expect(global.fetch).toHaveBeenCalledWith("http://test.url", {
        method: "POST",
        headers: {
          Accept: "text/html",
          "Content-Type": "application/json",
        },
        body: "{}",
        keepalive: true,
      });
    });

    it("should update html content", () => {
      expect(dalecContainer.innerHTML).toBe("<div>response</div>");
    });

    it("should not have the loading css class", () => {
      expect(dalecContainer.classList).not.toContain("dalec-loading");
    });
  });

  describe("with channelObjects and orderedBy", () => {
    beforeAll(() => {
      document.body.innerHTML = `
                <div id="dalec-1" data-url="http://test.url" data-channel-objects="[123,2,34]" data-ordered-by="name"></div>
            `;
      global.fetch = jest.fn(() =>
        Promise.resolve({
          ok: true,
          text: () => Promise.resolve("<div>response</div>"),
        }),
      ) as jest.Mock;
      dalecContainer = document.getElementById("dalec-1");
      fetch_content(dalecContainer);
    });

    it("should call fetch with channelObjects and orderedBy", () => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          body: '{"channelObjects":[123,2,34],"orderedBy":"name"}',
        }),
      );
    });
  });
  describe("with channelObjects but no orderedBy", () => {
    beforeAll(() => {
      document.body.innerHTML = `
                <div id="dalec-1" data-url="http://test.url" data-channel-objects="[123,2,34]"></div>
            `;
      global.fetch = jest.fn(() =>
        Promise.resolve({
          ok: true,
          text: () => Promise.resolve("<div>response</div>"),
        }),
      ) as jest.Mock;
      dalecContainer = document.getElementById("dalec-1");
      fetch_content(dalecContainer);
    });

    it("should call fetch with channelObjects", () => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          body: '{"channelObjects":[123,2,34]}',
        }),
      );
    });
  });

  describe("with orderedBy but no channelObjects", () => {
    beforeAll(() => {
      document.body.innerHTML = `
                <div id="dalec-1" data-url="http://test.url" data-ordered-by="name"></div>
            `;
      global.fetch = jest.fn(() =>
        Promise.resolve({
          ok: true,
          text: () => Promise.resolve("<div>response</div>"),
        }),
      ) as jest.Mock;
      dalecContainer = document.getElementById("dalec-1");
      fetch_content(dalecContainer);
    });

    it("should call fetch with orderedBy", () => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          body: '{"orderedBy":"name"}',
        }),
      );
    });
  });
  describe("when fetch fails", () => {
    beforeAll(() => {
      document.body.innerHTML = `
                <div id="dalec-1" data-url="http://test.url"></div>
            `;
      global.fetch = jest.fn(() =>
        Promise.resolve({
          ok: false,
          status: 500,
        }),
      ) as jest.Mock;
      dalecContainer = document.getElementById("dalec-1");
      fetch_content(dalecContainer);
    });

    it("should not have the loading css class", () => {
      expect(dalecContainer.classList).not.toContain("dalec-loading");
    });

    it("should have the loading-error css class", () => {
      expect(dalecContainer.classList).toContain("dalec-loading-error");
    });
  });
});
