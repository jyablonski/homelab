package main

import (
	"fmt"
	"log"
	"time"
)

type Dog struct {
	Name string
	Age  int
}

type Human struct {
	Name string
	Age  int
}

type Mammal interface {
	Eat()
}

func (d Dog) Eat() {
	log.Printf("%s is eating dog food.\n", d.Name)
}

func (h Human) Eat() {
	log.Printf("%s is eating human food.\n", h.Name)
}

func EatSomething(m Mammal) error {
	m.Eat()
	return nil
}

// Takes a copy - changes don't affect original
func HaveBirthday(d Dog) {
	d.Age++
	log.Printf("(copy) %s is now %d inside function\n", d.Name, d.Age)
}

// Takes a pointer - changes affect original
func HaveBirthdayPointer(d *Dog) {
	d.Age++ // Go automatically dereferences, same as (*d).Age++
	log.Printf("(pointer) %s is now %d inside function\n", d.Name, d.Age)
}

func main() {
	log.Println("Start time:", time.Now().UTC())
	time.Sleep(1 * time.Second)
	log.Println("End time:", time.Now().UTC())

	d := Dog{Name: "Buddy", Age: 3}
	d.Eat()

	j := Human{Name: "Alice", Age: 30}
	j.Eat()

	EatSomething(d)
	EatSomething(j)

	// ========== POINTER EXAMPLES ==========

	fmt.Println("\n--- Pointer Basics ---")

	x := 42
	p := &x // p is a pointer to x (stores x's memory address)

	fmt.Printf("x value: %d\n", x)
	fmt.Printf("x address: %p\n", &x)
	fmt.Printf("p value (address it holds): %p\n", p)
	fmt.Printf("p dereferenced (*p): %d\n", *p)

	*p = 100 // modify x through the pointer
	fmt.Printf("x after *p = 100: %d\n", x)

	fmt.Println("\n--- Pass by Value vs Pointer ---")

	dog1 := Dog{Name: "Rex", Age: 5}
	fmt.Printf("Before HaveBirthday: %s is %d\n", dog1.Name, dog1.Age)
	HaveBirthday(dog1) // passes a copy
	fmt.Printf("After HaveBirthday: %s is still %d (unchanged)\n", dog1.Name, dog1.Age)

	fmt.Println()

	dog2 := Dog{Name: "Max", Age: 7}
	fmt.Printf("Before HaveBirthdayPointer: %s is %d\n", dog2.Name, dog2.Age)
	HaveBirthdayPointer(&dog2) // passes address
	fmt.Printf("After HaveBirthdayPointer: %s is now %d (changed!)\n", dog2.Name, dog2.Age)

	fmt.Println("\n--- Nil Pointers ---")

	var nilPointer *int // declared but not initialized, defaults to nil
	fmt.Printf("nilPointer value: %v\n", nilPointer)
	fmt.Printf("nilPointer is nil: %t\n", nilPointer == nil)
	// fmt.Println(*nilPointer) // would panic! can't dereference nil

	fmt.Println("\n--- Pointers to Structs ---")

	dogPtr := &Dog{Name: "Luna", Age: 2} // create and get pointer in one step
	fmt.Printf("dogPtr address: %p\n", dogPtr)
	fmt.Printf("dogPtr.Name: %s\n", dogPtr.Name)       // auto-dereferenced
	fmt.Printf("(*dogPtr).Name: %s\n", (*dogPtr).Name) // explicit dereference (same thing)

	fmt.Println("\n--- new() vs & ---")

	// Two ways to get a pointer
	p1 := new(int)               // allocates zeroed int, returns pointer
	p2 := &struct{ x int }{x: 5} // takes address of a value

	fmt.Printf("new(int) gives: %d (zero value)\n", *p1)
	fmt.Printf("&struct{}{x: 5} gives: %d\n", p2.x)
}
