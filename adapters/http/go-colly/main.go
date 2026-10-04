package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"os"
	"sort"
	"strconv"
	"time"

	"github.com/gocolly/colly/v2"
)

type item struct {
	Index int
	Value string
}

func main() {
	base := flag.String("base", "", "fixture base URL")
	count := flag.Int("count", 0, "request count")
	concurrency := flag.Int("concurrency", 1, "parallel requests")
	delay := flag.Int("delay-ms", 0, "server delay")
	flag.Parse()
	collector := colly.NewCollector(colly.Async(true), colly.MaxDepth(1))
	if err := collector.Limit(&colly.LimitRule{DomainGlob: "*", Parallelism: *concurrency}); err != nil {
		panic(err)
	}
	results := make(chan item, *count)
	collector.OnHTML("span.value", func(element *colly.HTMLElement) {
		index, err := strconv.Atoi(element.Request.Ctx.Get("index"))
		if err != nil {
			panic(err)
		}
		results <- item{index, element.Text}
	})
	started := time.Now()
	for index := 0; index < *count; index++ {
		ctx := colly.NewContext()
		ctx.Put("index", strconv.Itoa(index))
		url := fmt.Sprintf("%s/page?id=%d&delayMs=%d", *base, index, *delay)
		if err := collector.Request("GET", url, nil, ctx, nil); err != nil {
			panic(err)
		}
	}
	collector.Wait()
	close(results)
	items := make([]item, 0, *count)
	for value := range results {
		items = append(items, value)
	}
	sort.Slice(items, func(i, j int) bool { return items[i].Index < items[j].Index })
	values := make([]string, len(items))
	status := "ok"
	for index, value := range items {
		values[index] = value.Value
		if value.Value != fmt.Sprintf("value-%d", index) {
			status = "wrongOutput"
		}
	}
	wall := time.Since(started).Nanoseconds()
	result := map[string]any{"armId": "colly", "language": "go", "count": *count, "concurrency": *concurrency, "delayMs": *delay, "wallNs": wall, "throughputRequestsPerSecond": float64(*count) / (float64(wall) / 1e9), "terminalStatus": status, "values": values}
	if err := json.NewEncoder(os.Stdout).Encode(result); err != nil {
		panic(err)
	}
	if status != "ok" {
		os.Exit(2)
	}
}
