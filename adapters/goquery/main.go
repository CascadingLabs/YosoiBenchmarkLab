package main

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"os"
	"runtime"
	"strings"
	"time"

	"github.com/PuerkitoBio/goquery"
	"github.com/andybalholm/cascadia"
)

type output struct {
	SchemaVersion       string   `json:"schemaVersion"`
	ArmID               string   `json:"armId"`
	Language            string   `json:"language"`
	Runtime             string   `json:"runtime"`
	ProductVersion      string   `json:"productVersion"`
	Task                string   `json:"task"`
	Phase               string   `json:"phase"`
	TerminalStatus      string   `json:"terminalStatus"`
	MatchCount          int      `json:"matchCount"`
	Values              []string `json:"values"`
	OutputSHA256        string   `json:"outputSha256"`
	SamplesNS           []int64  `json:"samplesNs"`
	OperationsPerSample int      `json:"operationsPerSample"`
	InputBytes          int      `json:"inputBytes"`
}

func selectorFor(task string) (string, error) {
	switch task {
	case "caveman":
		return `article.product-card[data-sku="sku-000073"] span.price`, nil
	case "hard":
		return `article.product-card[data-selected="true"] span.price`, nil
	default:
		return "", fmt.Errorf("unsupported task: %s", task)
	}
}

func parse(data []byte) (*goquery.Document, error) {
	return goquery.NewDocumentFromReader(bytes.NewReader(data))
}

func locate(document *goquery.Document, matcher goquery.Matcher) []string {
	values := make([]string, 0)
	document.FindMatcher(matcher).Each(func(_ int, selection *goquery.Selection) {
		values = append(values, strings.Join(strings.Fields(selection.Text()), " "))
	})
	return values
}

func equalValues(left []string, right []string) bool {
	if len(left) != len(right) {
		return false
	}
	for index := range left {
		if left[index] != right[index] {
			return false
		}
	}
	return true
}

func digestValues(values []string) (string, error) {
	data, err := json.Marshal(values)
	if err != nil {
		return "", err
	}
	digest := sha256.Sum256(data)
	return hex.EncodeToString(digest[:]), nil
}

func run() error {
	fixture := flag.String("fixture", "", "fixture path")
	task := flag.String("task", "", "benchmark task")
	phase := flag.String("phase", "", "measurement phase")
	samples := flag.Int("samples", 0, "sample count")
	operations := flag.Int("operations", 0, "operations per sample")
	flag.Parse()
	if *fixture == "" || *task == "" || *phase == "" {
		return errors.New("fixture, task, and phase are required")
	}
	if *samples < 0 || *operations < 1 {
		return errors.New("samples must be non-negative and operations must be positive")
	}

	data, err := os.ReadFile(*fixture)
	if err != nil {
		return err
	}
	selector, err := selectorFor(*task)
	if err != nil {
		return err
	}
	matcher, err := cascadia.Compile(selector)
	if err != nil {
		return err
	}
	parsed, err := parse(data)
	if err != nil {
		return err
	}
	expectedValues := locate(parsed, matcher)
	samplesNS := make([]int64, 0, *samples)

	for sample := 0; sample < *samples; sample++ {
		started := time.Now()
		var lastValues []string
		switch *phase {
		case "parse":
			for operation := 0; operation < *operations; operation++ {
				if _, err = parse(data); err != nil {
					return err
				}
			}
			lastValues = expectedValues
		case "locate":
			for operation := 0; operation < *operations; operation++ {
				lastValues = locate(parsed, matcher)
			}
		case "endToEnd":
			for operation := 0; operation < *operations; operation++ {
				var document *goquery.Document
				document, err = parse(data)
				if err != nil {
					return err
				}
				lastValues = locate(document, matcher)
			}
		default:
			return fmt.Errorf("unsupported phase: %s", *phase)
		}
		elapsed := time.Since(started).Nanoseconds() / int64(*operations)
		if *phase != "parse" && !equalValues(lastValues, expectedValues) {
			return errors.New("measured output changed from correctness preflight")
		}
		samplesNS = append(samplesNS, elapsed)
	}

	digest, err := digestValues(expectedValues)
	if err != nil {
		return err
	}
	result := output{
		SchemaVersion:       "yosoi.benchmark.adapter.v1",
		ArmID:               "goquery",
		Language:            "go",
		Runtime:             runtime.Version(),
		ProductVersion:      "1.12.0",
		Task:                *task,
		Phase:               *phase,
		TerminalStatus:      "ok",
		MatchCount:          len(expectedValues),
		Values:              expectedValues,
		OutputSHA256:        digest,
		SamplesNS:           samplesNS,
		OperationsPerSample: *operations,
		InputBytes:          len(data),
	}
	return json.NewEncoder(os.Stdout).Encode(result)
}

func main() {
	if err := run(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
