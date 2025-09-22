import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { Pagination, buildPaginationRange } from "@/components/gyms/Pagination";

describe("Pagination", () => {
  it("generates a contiguous range when the total page count is small", () => {
    expect(buildPaginationRange(2, 5)).toEqual([1, 2, 3, 4, 5]);
  });

  it("shows ellipsis when the range is truncated", () => {
    expect(buildPaginationRange(10, 20)).toEqual([1, "ellipsis", 9, 10, 11, "ellipsis", 20]);
  });

  it("renders page controls and emits changes on interaction", async () => {
    const user = userEvent.setup();
    const onChange = jest.fn();

    render(
      <Pagination
        currentPage={2}
        hasNextPage
        onChange={onChange}
        totalPages={5}
      />,
    );

    expect(screen.getByRole("button", { name: "ページ 1" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "ページ 2" })).toHaveAttribute("aria-current", "page");

    await user.click(screen.getByRole("button", { name: "ページ 3" }));
    expect(onChange).toHaveBeenCalledWith(3);

    await user.click(screen.getByRole("button", { name: "前のページ" }));
    expect(onChange).toHaveBeenCalledWith(1);
  });

  it("disables navigation buttons at the boundaries", () => {
    const onChange = jest.fn();

    render(
      <Pagination
        currentPage={3}
        hasNextPage={false}
        isLoading={false}
        onChange={onChange}
        totalPages={3}
      />,
    );

    expect(screen.getByRole("button", { name: "前のページ" })).not.toBeDisabled();
    expect(screen.getByRole("button", { name: "次のページ" })).toBeDisabled();

    render(
      <Pagination
        currentPage={1}
        hasNextPage={false}
        isLoading={true}
        onChange={onChange}
        totalPages={3}
      />,
    );

    expect(screen.getAllByRole("button", { name: "前のページ" })[1]).toBeDisabled();
    expect(screen.getAllByRole("button", { name: "次のページ" })[1]).toBeDisabled();
  });
});
