package main

import (
	"context"
	"fmt"

	sitter "github.com/smacker/go-tree-sitter"
	python "github.com/smacker/go-tree-sitter/python"
)

func main() {
	// parser := sitter.NewParser()
	lang := python.GetLanguage()

	sourceCode := []byte(
		`self.warnings['sos']
		self.errors['sos']
		self.warnings['ses]`)

	selfWarningsQuery := `(subscript
		value: (attribute
			object: (identifier) @object (#eq? @object "self")
			attribute: (identifier) @attribute (#eq? @attribute "warnings"))
		subscript: (string))`

	n, _ := sitter.ParseCtx(context.Background(), sourceCode, lang)

	fmt.Println(n)

	q, err := sitter.NewQuery([]byte(selfWarningsQuery), lang)
	if err != nil {
		panic(err)
	}
	qc := sitter.NewQueryCursor()
	qc.Exec(q, n)

	for {
		m, ok := qc.NextMatch()
		if !ok {
			break
		}
		// Apply predicates filtering
		m = qc.FilterPredicates(m, sourceCode)
		for _, c := range m.Captures {
			fmt.Println(c.Node.Content(sourceCode))
		}
	}
}
