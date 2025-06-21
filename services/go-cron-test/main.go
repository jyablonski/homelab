package main

import (
	"log"
	"time"
)

func main() {
	log.Println("Start time:", time.Now().UTC())

	time.Sleep(10 * time.Second)

	log.Println("End time:", time.Now().UTC())
}
