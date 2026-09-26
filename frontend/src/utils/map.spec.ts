import { describe, expect, it } from 'vitest'
import { splitRoute, unwrap } from './map'

describe('map utils', () => {
  it('splits a route at the progress point', () => {
    const { done, todo } = splitRoute(
      [
        [0, 0],
        [0, 10],
        [0, 20],
      ],
      0.25,
    )
    expect(done).toEqual([
      [0, 0],
      [0, 5],
    ])
    expect(todo[0]).toEqual([0, 5])
    expect(todo[todo.length - 1]).toEqual([0, 20])
  })

  it('handles the ends of the route', () => {
    const route: [number, number][] = [
      [0, 0],
      [0, 10],
    ]
    expect(splitRoute(route, 0).done).toEqual([
      [0, 0],
      [0, 0],
    ])
    expect(splitRoute(route, 1).todo).toEqual([
      [0, 10],
      [0, 10],
    ])
  })

  it('unwraps routes across the antimeridian so lines take the short way', () => {
    expect(
      unwrap([
        [35, 170],
        [40, -170],
      ]),
    ).toEqual([
      [35, 170],
      [40, 190],
    ])
  })
})
